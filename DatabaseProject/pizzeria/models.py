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


class OrderItemType(models.TextChoices):
    PIZZA = "pizza", "Pizza"
    DRINK = "drink", "Drink"
    DESSERT = "dessert", "Dessert"


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


class Customer(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    birthdate = models.DateField()
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30)
    street = models.CharField(max_length=150)
    city = models.CharField(max_length=80)
    postal_code = models.CharField(max_length=12)
    country = models.CharField(max_length=80, default="Belgium")
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


class DeliveryPerson(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=30, unique=True)
    postal_code = models.CharField(max_length=12)
    last_delivery_completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


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
    total_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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


class OrderItem(models.Model):
    order = models.ForeignKey(
        CustomerOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_type = models.CharField(max_length=20, choices=OrderItemType.choices)
    pizza = models.ForeignKey(
        Pizza,
        on_delete=models.SET_NULL,
        related_name="order_items",
        null=True,
        blank=True,
    )
    item_name_snapshot = models.CharField(max_length=120)
    quantity = models.PositiveIntegerField(default=1)
    unit_price_at_order = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name="order_item_quantity_gt_0",
            ),
            models.CheckConstraint(
                check=(
                    models.Q(item_type=OrderItemType.PIZZA, pizza__isnull=False)
                    | (~models.Q(item_type=OrderItemType.PIZZA) & models.Q(pizza__isnull=True))
                ),
                name="order_item_pizza_presence",
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
