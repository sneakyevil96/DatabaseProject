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


@admin.register(models.PostalArea)
class PostalAreaAdmin(admin.ModelAdmin):
    list_display = ("postal_code", "city", "country")
    search_fields = ("postal_code", "city")
    list_filter = ("country",)


@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "email", "phone", "postal_code")
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "postal_area__postal_code",
        "postal_area__city",
    )
    list_filter = ("postal_area", "gender")
    list_select_related = ("postal_area",)


@admin.register(models.DeliveryPerson)
class DeliveryPersonAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "phone", "postal_code", "is_active")
    list_filter = ("is_active", "postal_area")
    search_fields = ("first_name", "last_name", "phone", "postal_area__postal_code")
    list_select_related = ("postal_area",)


@admin.register(models.DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "discount_value", "is_active", "is_one_time", "usage_limit", "used_count")
    list_filter = ("discount_type", "is_active", "is_one_time")
    search_fields = ("code", "description")


class OrderItemInline(admin.TabularInline):
    model = models.OrderItem
    extra = 0
    fields = (
        "content_type",
        "object_id",
        "item_name_snapshot",
        "quantity",
        "base_price",
        "unit_price_at_order",
    )
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
    list_display = ("order", "item_name_snapshot", "product_type", "quantity", "unit_price_at_order")
    list_filter = ("content_type",)
    autocomplete_fields = ("order",)
    search_fields = ("item_name_snapshot", "order__id")
    list_select_related = ("order", "content_type")

    def product_type(self, obj):
        return obj.content_type.model if obj.content_type_id else ""

    product_type.short_description = "Product type"


@admin.register(models.OrderAdjustment)
class OrderAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("order", "adjustment_type", "amount", "created_at")
    list_filter = ("adjustment_type",)
    autocomplete_fields = ("order",)
    search_fields = ("order__id",)


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


@admin.register(models.Drink)
class DrinkAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price_eur", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "category")


@admin.register(models.Dessert)
class DessertAdmin(admin.ModelAdmin):
    list_display = ("name", "price_eur", "is_vegan", "is_active")
    list_filter = ("is_vegan", "is_active")
    search_fields = ("name", "description")


@admin.register(models.DessertIngredient)
class DessertIngredientAdmin(admin.ModelAdmin):
    list_display = ("dessert", "ingredient")
    search_fields = ("dessert__name", "ingredient")
    autocomplete_fields = ("dessert",)


@admin.register(models.CustomerLoyalty)
class CustomerLoyaltyAdmin(admin.ModelAdmin):
    list_display = ("customer", "lifetime_pizzas", "pizzas_since_last_reward", "updated_at")
    search_fields = ("customer__first_name", "customer__last_name", "customer__email")


@admin.register(models.CustomerDiscountRedemption)
class CustomerDiscountRedemptionAdmin(admin.ModelAdmin):
    list_display = ("customer", "discount_code", "redeemed_at")
    search_fields = ("customer__first_name", "customer__last_name", "discount_code__code")
    autocomplete_fields = ("customer", "discount_code")


@admin.register(models.DeliveryZoneAssignment)
class DeliveryZoneAssignmentAdmin(admin.ModelAdmin):
    list_display = ("delivery_person", "postal_area", "postal_code_display", "priority")
    list_filter = ("postal_area",)
    search_fields = (
        "delivery_person__first_name",
        "delivery_person__last_name",
        "postal_area__postal_code",
        "postal_area__city",
    )
    autocomplete_fields = ("delivery_person", "postal_area")
    list_select_related = ("delivery_person", "postal_area")

    def postal_code_display(self, obj):
        return obj.postal_area.postal_code

    postal_code_display.short_description = "Postal code"


@admin.register(models.OrderDiscountApplication)
class OrderDiscountApplicationAdmin(admin.ModelAdmin):
    list_display = ("order", "discount_code", "amount", "applied_at")
    search_fields = ("order__id", "discount_code__code")
    autocomplete_fields = ("order", "discount_code")
