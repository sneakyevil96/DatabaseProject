"""Place customer orders with discounts and delivery assignment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.utils import timezone

from pizzeria.models import (
    Customer,
    CustomerDiscountRedemption,
    CustomerLoyalty,
    CustomerOrder,
    DeliveryPerson,
    DeliveryType,
    DiscountCode,
    DiscountType,
    Drink,
    Dessert,
    OrderDiscountApplication,
    OrderItem,
    OrderItemType,
    OrderStatus,
    PizzaPricing,
)


@dataclass
class ItemSpec:
    identifier: int
    quantity: int


@dataclass
class BirthdayDiscount:
    total: Decimal
    pizza_component: Decimal


class Command(BaseCommand):
    help = "Create an order, applying discounts and assigning delivery personnel."

    def add_arguments(self, parser):
        parser.add_argument('--customer-id', type=int, required=True)
        parser.add_argument('--pizza', action='append', default=[], help='Format: <pizza_id>[:qty]')
        parser.add_argument('--drink', action='append', default=[], help='Format: <drink_id>[:qty]')
        parser.add_argument('--dessert', action='append', default=[], help='Format: <dessert_id>[:qty]')
        parser.add_argument('--discount-code', help='Optional discount code to apply')
        parser.add_argument('--delivery-type', choices=[DeliveryType.DELIVERY, DeliveryType.PICKUP], default=DeliveryType.DELIVERY)
        parser.add_argument('--notes', default='')

    def handle(self, *args, **options):
        pizzas = self._parse_specs(options['pizza'], 'pizza')
        if not pizzas:
            raise CommandError('At least one pizza must be included in the order.')
        drinks = self._parse_specs(options['drink'], 'drink')
        desserts = self._parse_specs(options['dessert'], 'dessert')

        try:
            customer = Customer.objects.select_related('loyalty').get(pk=options['customer_id'])
        except Customer.DoesNotExist as exc:
            raise CommandError(f"Customer {options['customer_id']} not found") from exc

        discount_code = self._resolve_discount_code(options.get('discount_code'))
        delivery_type = options['delivery_type']
        notes = options['notes']
        order_datetime = timezone.now()

        with transaction.atomic():
            loyalty = getattr(customer, 'loyalty', None)
            if loyalty is None:
                loyalty = CustomerLoyalty.objects.create(customer=customer)

            self._validate_discount_code_usage(customer, discount_code)
            order_data = self._build_order_items(pizzas, drinks, desserts)

            subtotal = order_data['subtotal']
            pizza_subtotal = order_data['pizza_subtotal']
            pizza_count = order_data['pizza_count']

            birthday_discount = self._compute_birthday_discount(customer, order_datetime, order_data['items'])
            loyalty_discount = self._compute_loyalty_discount(loyalty, pizza_count, pizza_subtotal, birthday_discount.pizza_component)
            code_discount = self._compute_code_discount(discount_code, subtotal - birthday_discount.total - loyalty_discount)

            discount_total = (birthday_discount.total + loyalty_discount + code_discount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            subtotal = subtotal.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            total_due = (subtotal - discount_total).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            birthday_amount = birthday_discount.total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            loyalty_amount = loyalty_discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            code_amount = code_discount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            order = CustomerOrder.objects.create(
                customer=customer,
                order_datetime=order_datetime,
                status=OrderStatus.PENDING,
                delivery_type=delivery_type,
                subtotal_amount=subtotal,
                discount_amount=discount_total,
                total_due=total_due,
                loyalty_discount_amount=loyalty_amount,
                birthday_discount_amount=birthday_amount,
                code_discount_amount=code_amount,
                applied_discount_code=discount_code,
                notes=notes,
            )

            for payload in order_data['items']:
                OrderItem.objects.create(
                    order=order,
                    item_type=payload['type'],
                    pizza=payload.get('pizza'),
                    drink=payload.get('drink'),
                    dessert=payload.get('dessert'),
                    item_name_snapshot=payload['name'],
                    quantity=payload['quantity'],
                    base_price=payload['price'],
                    unit_price_at_order=payload['price'],
                )

            if discount_code:
                self._apply_discount_code(customer, discount_code, order, code_amount)

            self._update_loyalty(loyalty)
            self._assign_delivery(order, customer, delivery_type, order_datetime)

        self.stdout.write(
            self.style.SUCCESS(
                f"Order #{order.pk} placed. Subtotal: EUR {subtotal} | Discounts: EUR {discount_total} | Total due: EUR {total_due}"
            )
        )

    def _parse_specs(self, raw_values: list[str], label: str) -> list[ItemSpec]:
        specs: list[ItemSpec] = []
        for raw in raw_values:
            if ':' in raw:
                ident, qty = raw.split(':', 1)
            else:
                ident, qty = raw, '1'
            if not ident.isdigit() or not qty.isdigit():
                raise CommandError(f"Invalid {label} specification: {raw}")
            identifier = int(ident)
            quantity = int(qty)
            if quantity <= 0:
                raise CommandError(f"Quantity must be positive for {label} {identifier}")
            specs.append(ItemSpec(identifier=identifier, quantity=quantity))
        return specs

    def _build_order_items(self, pizzas: list[ItemSpec], drinks: list[ItemSpec], desserts: list[ItemSpec]):
        items = []
        subtotal = Decimal('0')
        pizza_subtotal = Decimal('0')
        pizza_count = 0

        pizza_ids = [spec.identifier for spec in pizzas]
        pricing_map = {pricing.pizza_id: pricing for pricing in PizzaPricing.objects.filter(pizza__id__in=pizza_ids)}
        missing_pizzas = sorted({pid for pid in pizza_ids if pid not in pricing_map})
        if missing_pizzas:
            raise CommandError(f"Unknown or inactive pizza(s): {', '.join(str(m) for m in missing_pizzas)}")

        for spec in pizzas:
            pricing = pricing_map[spec.identifier]
            price = Decimal(pricing.final_price_with_vat)
            pizza_subtotal += price * spec.quantity
            pizza_count += spec.quantity
            subtotal += price * spec.quantity
            items.append({
                'type': OrderItemType.PIZZA,
                'pizza': pricing.pizza,
                'drink': None,
                'dessert': None,
                'name': pricing.pizza.name,
                'quantity': spec.quantity,
                'price': price,
            })

        if drinks:
            drink_ids = [spec.identifier for spec in drinks]
            drink_map = {drink.id: drink for drink in Drink.objects.filter(pk__in=drink_ids, is_active=True)}
            missing_drinks = sorted({did for did in drink_ids if did not in drink_map})
            if missing_drinks:
                raise CommandError(f"Unknown drink(s): {', '.join(str(m) for m in missing_drinks)}")
            for spec in drinks:
                drink = drink_map[spec.identifier]
                price = Decimal(drink.price_eur)
                subtotal += price * spec.quantity
                items.append({
                    'type': OrderItemType.DRINK,
                    'pizza': None,
                    'drink': drink,
                    'dessert': None,
                    'name': drink.name,
                    'quantity': spec.quantity,
                    'price': price,
                })

        if desserts:
            dessert_ids = [spec.identifier for spec in desserts]
            dessert_map = {dessert.id: dessert for dessert in Dessert.objects.filter(pk__in=dessert_ids, is_active=True)}
            missing_desserts = sorted({did for did in dessert_ids if did not in dessert_map})
            if missing_desserts:
                raise CommandError(f"Unknown dessert(s): {', '.join(str(m) for m in missing_desserts)}")
            for spec in desserts:
                dessert = dessert_map[spec.identifier]
                price = Decimal(dessert.price_eur)
                subtotal += price * spec.quantity
                items.append({
                    'type': OrderItemType.DESSERT,
                    'pizza': None,
                    'drink': None,
                    'dessert': dessert,
                    'name': dessert.name,
                    'quantity': spec.quantity,
                    'price': price,
                })

        return {
            'items': items,
            'subtotal': subtotal,
            'pizza_subtotal': pizza_subtotal,
            'pizza_count': pizza_count,
        }

    def _compute_birthday_discount(self, customer: Customer, order_datetime, items) -> BirthdayDiscount:
        if customer.birthdate is None:
            return BirthdayDiscount(total=Decimal('0'), pizza_component=Decimal('0'))
        if (customer.birthdate.month, customer.birthdate.day) != (order_datetime.month, order_datetime.day):
            return BirthdayDiscount(total=Decimal('0'), pizza_component=Decimal('0'))

        cheapest_pizza = None
        cheapest_drink = None
        for item in items:
            price = item['price']
            if item['type'] == OrderItemType.PIZZA:
                if cheapest_pizza is None or price < cheapest_pizza:
                    cheapest_pizza = price
            elif item['type'] == OrderItemType.DRINK:
                if cheapest_drink is None or price < cheapest_drink:
                    cheapest_drink = price

        total = Decimal('0')
        pizza_component = Decimal('0')
        if cheapest_pizza is not None:
            total += cheapest_pizza
            pizza_component = cheapest_pizza
        if cheapest_drink is not None:
            total += cheapest_drink
        return BirthdayDiscount(total=total, pizza_component=pizza_component)

    def _compute_loyalty_discount(self, loyalty: CustomerLoyalty, pizza_count: int, pizza_subtotal: Decimal, birthday_pizza_component: Decimal) -> Decimal:
        if pizza_count <= 0:
            return Decimal('0')
        total_pizzas = loyalty.pizzas_since_last_reward + pizza_count
        reward_cycles, remainder = divmod(total_pizzas, 10)
        discount = Decimal('0')
        if reward_cycles > 0 and pizza_subtotal > 0:
            eligible_base = max(pizza_subtotal - birthday_pizza_component, Decimal('0'))
            discount = (eligible_base * Decimal('0.10'))
        loyalty.pizzas_since_last_reward = remainder
        loyalty.lifetime_pizzas += pizza_count
        return discount

    def _compute_code_discount(self, discount_code: DiscountCode | None, taxable_amount: Decimal) -> Decimal:
        if not discount_code or taxable_amount <= 0:
            return Decimal('0')
        value = Decimal(discount_code.discount_value)
        if discount_code.discount_type == DiscountType.PERCENTAGE:
            return taxable_amount * (value / Decimal('100'))
        return min(value, taxable_amount)

    def _validate_discount_code_usage(self, customer: Customer, discount_code: DiscountCode | None) -> None:
        if not discount_code:
            return
        if discount_code.is_one_time and CustomerDiscountRedemption.objects.filter(customer=customer, discount_code=discount_code).exists():
            raise CommandError(f"Discount code {discount_code.code} has already been used by this customer")

    def _apply_discount_code(self, customer: Customer, discount_code: DiscountCode, order: CustomerOrder, amount: Decimal) -> None:
        if amount <= 0:
            return
        discount_code.used_count = min(discount_code.usage_limit, discount_code.used_count + 1)
        discount_code.save(update_fields=['used_count'])
        CustomerDiscountRedemption.objects.get_or_create(customer=customer, discount_code=discount_code)
        OrderDiscountApplication.objects.create(order=order, discount_code=discount_code, amount=amount)

    def _update_loyalty(self, loyalty: CustomerLoyalty) -> None:
        loyalty.save(update_fields=['lifetime_pizzas', 'pizzas_since_last_reward', 'updated_at'])

    def _assign_delivery(self, order: CustomerOrder, customer: Customer, delivery_type: str, order_datetime) -> None:
        if delivery_type != DeliveryType.DELIVERY:
            return
        delivery_person = (
            DeliveryPerson.objects
            .select_for_update(skip_locked=True)
            .filter(is_active=True, zone_assignments__postal_code=customer.postal_code)
            .filter(models.Q(next_available_at__isnull=True) | models.Q(next_available_at__lte=order_datetime))
            .order_by('zone_assignments__priority', 'next_available_at', 'id')
            .first()
        )
        if delivery_person is None:
            raise CommandError(f"No delivery person available for postal code {customer.postal_code}")

        delivery_person.next_available_at = order_datetime + timedelta(minutes=30)
        delivery_person.save(update_fields=['next_available_at'])
        order.delivery_person = delivery_person
        order.driver_assigned_at = order_datetime
        order.save(update_fields=['delivery_person', 'driver_assigned_at'])

    def _resolve_discount_code(self, code_value: str | None) -> DiscountCode | None:
        if not code_value:
            return None
        try:
            discount_code = DiscountCode.objects.get(code__iexact=code_value.strip())
        except DiscountCode.DoesNotExist as exc:
            raise CommandError(f"Discount code {code_value} not found") from exc
        today = timezone.now().date()
        if not discount_code.is_active or discount_code.valid_from > today or (discount_code.valid_until and discount_code.valid_until < today):
            raise CommandError(f"Discount code {discount_code.code} is not currently valid")
        if discount_code.used_count >= discount_code.usage_limit:
            raise CommandError(f"Discount code {discount_code.code} has been fully redeemed")
        return discount_code





