"""HTTP views for the pizzeria app."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .models import Dessert, Drink, PizzaPricing


def menu_view(request: HttpRequest) -> HttpResponse:
    """Render the pizza menu with dynamic pricing information."""
    include_cost = request.GET.get("include_cost") in {"1", "true", "True"}

    pizzas = (
        PizzaPricing.objects.filter(pizza__is_active=True)
        .select_related("pizza")
        .order_by("pizza__name")
    )
    drinks = Drink.objects.filter(is_active=True).order_by("name")
    desserts = Dessert.objects.filter(is_active=True).order_by("name")

    context = {
        "pizzas": pizzas,
        "include_cost": include_cost,
        "drinks": drinks,
        "desserts": desserts,
    }
    return render(request, "pizzeria/menu.html", context)
