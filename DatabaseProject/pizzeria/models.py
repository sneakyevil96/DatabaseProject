from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PREPARING = "preparing", "Preparing"
    OUT_FOR_DELIVERY = "out_for_delivery", "Out for delivery"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"


class DeliveryType(models.TextChoices):
    DELIVERY = "delivery", "Delivery"
    PICKUP = "pickup", "Pickup"


class OrderAdjustmentType(models.TextChoices):
    LOYALTY = "loyalty", "Loyalty discount"
    BIRTHDAY = "birthday", "Birthday discount"


class DiscountType(models.TextChoices):
    PERCENTAGE = "percentage", "Percentage"
    FIXED_AMOUNT = "fixed_amount", "Fixed amount"


class Ingredient(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_meat = models.BooleanField(default=False)
    is_dairy = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    unit_type = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(unit_cost__gt=0),
                name="ingredient_unit_cost_gt_0",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Pizza(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    ingredients = models.ManyToManyField(
        Ingredient,
        through="PizzaIngredient",
        related_name="pizzas",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PizzaIngredient(models.Model):
    pizza = models.ForeignKey(Pizza, on_delete=models.CASCADE, related_name="pizza_ingredients")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.RESTRICT, related_name="pizza_ingredients")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    position = models.PositiveSmallIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("pizza", "ingredient")
        ordering = ["pizza", "position", "ingredient__name"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name="pizza_ingredient_quantity_gt_0",
            )
        ]

    def __str__(self) -> str:
        return f"{self.pizza} -> {self.ingredient} ({self.quantity})"


class PostalArea(models.Model):
    postal_code = models.CharField(max_length=12, unique=True)
    city = models.CharField(max_length=80, blank=True)
    country = models.CharField(max_length=80, default="Belgium")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["postal_code"]

    def __str__(self) -> str:
        return f"{self.postal_code} {self.city}"


class Customer(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    birthdate = models.DateField()
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30)
    street = models.CharField(max_length=150)
    postal_area = models.ForeignKey(
        PostalArea,
        on_delete=models.PROTECT,
        related_name="customers",
    )
    gender = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(birthdate__lte=Now()),
                name="customer_birthdate_not_future",
            )
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def city(self) -> str:
        return self.postal_area.city

    @property
    def postal_code(self) -> str:
        return self.postal_area.postal_code

    @property
    def country(self) -> str:
        return self.postal_area.country


class DeliveryPerson(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=30, unique=True)
    postal_area = models.ForeignKey(
        PostalArea,
        on_delete=models.PROTECT,
        related_name="delivery_people",
    )
    last_delivery_completed_at = models.DateTimeField(null=True, blank=True)
    next_available_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def postal_code(self) -> str:
        return self.postal_area.postal_code


class DiscountCode(models.Model):
    code = models.CharField(max_length=40, unique=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=6, decimal_places=2)
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    is_one_time = models.BooleanField(default=True)
    usage_limit = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(discount_value__gt=0),
                name="discount_value_gt_0",
            ),
            models.CheckConstraint(
                check=models.Q(usage_limit__gt=0),
                name="usage_limit_gt_0",
            ),
            models.CheckConstraint(
                check=models.Q(used_count__gte=0),
                name="used_count_gte_0",
            ),
        ]

    def __str__(self) -> str:
        return self.code


class CustomerOrder(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    order_datetime = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryType.choices,
        default=DeliveryType.DELIVERY,
    )
    total_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    delivery_person = models.ForeignKey(
        DeliveryPerson,
        on_delete=models.SET_NULL,
        related_name="orders",
        null=True,
        blank=True,
    )
    driver_assigned_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-order_datetime"]

    def __str__(self) -> str:
        return f"Order #{self.pk}"

    def _adjustment_amount(self, adjustment_type: str) -> Decimal:
        adjustment = self.adjustments.filter(adjustment_type=adjustment_type).first()
        return adjustment.amount if adjustment else Decimal("0")

    @property
    def subtotal_amount(self) -> Decimal:
        total = Decimal("0")
        for item in self.items.all():
            total += item.unit_price_at_order * item.quantity
        return total

    @property
    def loyalty_discount_amount(self) -> Decimal:
        return self._adjustment_amount(OrderAdjustmentType.LOYALTY)

    @property
    def birthday_discount_amount(self) -> Decimal:
        return self._adjustment_amount(OrderAdjustmentType.BIRTHDAY)

    @property
    def code_discount_amount(self) -> Decimal:
        return sum(
            (application.amount for application in self.discount_applications.all()),
            Decimal("0"),
        )

    @property
    def discount_amount(self) -> Decimal:
        automatic = sum((adjustment.amount for adjustment in self.adjustments.all()), Decimal("0"))
        return automatic + self.code_discount_amount


class OrderAdjustment(models.Model):
    order = models.ForeignKey(
        CustomerOrder,
        on_delete=models.CASCADE,
        related_name="adjustments",
    )
    adjustment_type = models.CharField(max_length=20, choices=OrderAdjustmentType.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("order", "adjustment_type")
        ordering = ["order", "adjustment_type"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name="order_adjustment_amount_gt_0",
            )
        ]

    def __str__(self) -> str:
        return f"{self.order_id} -> {self.get_adjustment_type_display()} ({self.amount})"


class Drink(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50)
    price_eur = models.DecimalField(max_digits=6, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Dessert(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price_eur = models.DecimalField(max_digits=6, decimal_places=2)
    is_vegan = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class OrderItem(models.Model):
    order = models.ForeignKey(
        CustomerOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.PROTECT,
        limit_choices_to=models.Q(app_label="pizzeria", model__in=["pizza", "drink", "dessert"]),
    )
    object_id = models.PositiveIntegerField()
    product = GenericForeignKey("content_type", "object_id")
    item_name_snapshot = models.CharField(max_length=120)
    quantity = models.PositiveIntegerField(default=1)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price_at_order = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name="order_item_quantity_gt_0",
            ),
            models.CheckConstraint(
                check=models.Q(base_price__gte=0),
                name="order_item_base_price_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(unit_price_at_order__gte=0),
                name="order_item_unit_price_gte_0",
            ),
            models.UniqueConstraint(
                fields=["order", "content_type", "object_id"],
                name="order_item_unique_product",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.item_name_snapshot} x{self.quantity}"


class PizzaPricing(models.Model):
    pizza = models.OneToOneField(Pizza, primary_key=True, on_delete=models.DO_NOTHING)
    description = models.TextField(blank=True)
    is_active = models.BooleanField()
    ingredient_cost = models.DecimalField(max_digits=12, decimal_places=2)
    price_with_margin = models.DecimalField(max_digits=12, decimal_places=2)
    final_price_with_vat = models.DecimalField(max_digits=12, decimal_places=2)
    is_vegetarian_computed = models.BooleanField()
    is_vegan_computed = models.BooleanField()

    class Meta:
        managed = False
        db_table = "pizza_pricing"
        verbose_name = "Pizza pricing"
        verbose_name_plural = "Pizza pricing"

    def __str__(self) -> str:
        return f"{self.pizza.name} -> EUR {self.final_price_with_vat}"


class DessertIngredient(models.Model):
    dessert = models.ForeignKey(Dessert, on_delete=models.CASCADE, related_name="dessert_ingredients")
    ingredient = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("dessert", "ingredient")
        ordering = ["dessert", "ingredient"]

    def __str__(self) -> str:
        return f"{self.dessert.name}: {self.ingredient}"


class CustomerLoyalty(models.Model):
    customer = models.OneToOneField(Customer, related_name='loyalty', on_delete=models.CASCADE)
    lifetime_pizzas = models.PositiveIntegerField(default=0)
    pizzas_since_last_reward = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Loyalty<{self.customer_id}: {self.lifetime_pizzas} pizzas>"


class CustomerDiscountRedemption(models.Model):
    customer = models.ForeignKey(Customer, related_name='discount_redemptions', on_delete=models.CASCADE)
    discount_code = models.ForeignKey(DiscountCode, related_name='redemptions', on_delete=models.CASCADE)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("customer", "discount_code")
        ordering = ["-redeemed_at"]

    def __str__(self) -> str:
        return f"{self.customer} -> {self.discount_code}"


class DeliveryZoneAssignment(models.Model):
    delivery_person = models.ForeignKey(DeliveryPerson, related_name='zone_assignments', on_delete=models.CASCADE)
    postal_area = models.ForeignKey(PostalArea, related_name='zone_assignments', on_delete=models.CASCADE)
    priority = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("delivery_person", "postal_area")
        ordering = ["delivery_person", "priority", "postal_area__postal_code"]

    def __str__(self) -> str:
        return f"{self.delivery_person} -> {self.postal_area.postal_code}"


class OrderDiscountApplication(models.Model):
    order = models.ForeignKey(CustomerOrder, related_name='discount_applications', on_delete=models.CASCADE)
    discount_code = models.ForeignKey(DiscountCode, related_name='applied_orders', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-applied_at"]

    def __str__(self) -> str:
        return f"{self.order_id} -> {self.discount_code.code} ({self.amount})"
