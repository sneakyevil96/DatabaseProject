from django.contrib import admin

from . import models


class PizzaIngredientInline(admin.TabularInline):
    model = models.PizzaIngredient
    extra = 1
    autocomplete_fields = ("ingredient",)
    fields = ("ingredient", "quantity", "unit_type_display", "position")
    readonly_fields = ("unit_type_display",)

    def unit_type_display(self, obj):
        return obj.ingredient.unit_type if obj.ingredient_id else ""

    unit_type_display.short_description = "Unit"


@admin.register(models.Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "unit_cost", "unit_type", "is_meat", "is_dairy", "is_vegan")
    list_filter = ("is_meat", "is_dairy", "is_vegan")
    search_fields = ("name",)


@admin.register(models.Pizza)
class PizzaAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "is_vegetarian", "is_vegan")
    list_filter = ("is_active", "is_vegetarian", "is_vegan")
    search_fields = ("name", "description")
    inlines = [PizzaIngredientInline]


@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "phone", "postal_code")
    search_fields = ("first_name", "last_name", "email", "phone")
    list_filter = ("city", "postal_code", "gender")


@admin.register(models.DeliveryPerson)
class DeliveryPersonAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "phone", "postal_code", "is_active")
    list_filter = ("is_active", "postal_code")
    search_fields = ("first_name", "last_name", "phone")


@admin.register(models.DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "is_active", "is_one_time", "usage_limit", "used_count")
    list_filter = ("discount_type", "is_active", "is_one_time")
    search_fields = ("code", "description")


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    extra = 0
    autocomplete_fields = ("pizza",)
    readonly_fields = ("item_name_snapshot", "unit_price_at_order")


@admin.register(models.CustomerOrder)
class CustomerOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "order_datetime", "status", "delivery_type", "delivery_person")
    list_filter = ("status", "delivery_type", "delivery_person")
    search_fields = ("id", "customer__first_name", "customer__last_name", "customer__email")
    autocomplete_fields = ("customer", "delivery_person")
    inlines = [OrderItemInline]
    date_hierarchy = "order_datetime"


@admin.register(models.OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "item_name_snapshot", "item_type", "quantity", "unit_price_at_order")
    list_filter = ("item_type",)
    autocomplete_fields = ("order", "pizza")
    search_fields = ("item_name_snapshot", "order__id")


@admin.register(models.PizzaPricing)
class PizzaPricingAdmin(admin.ModelAdmin):
    list_display = (
        "pizza",
        "ingredient_cost",
        "price_with_margin",
        "final_price_with_vat",
        "is_vegetarian_computed",
        "is_vegan_computed",
    )
    search_fields = ("pizza__name",)
    readonly_fields = (
        "pizza",
        "description",
        "is_active",
        "ingredient_cost",
        "price_with_margin",
        "final_price_with_vat",
        "is_vegetarian_computed",
        "is_vegan_computed",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
