"""Management command to display menu pricing from pizza_pricing view."""

from decimal import Decimal

from django.core.management.base import BaseCommand

from pizzeria.models import PizzaPricing


class Command(BaseCommand):
    help = "Display active pizzas with computed pricing information."

    def add_arguments(self, parser):
        parser.add_argument(
            "--include-cost",
            action="store_true",
            help="Include ingredient cost column in the output.",
        )

    def handle(self, *args, **options):
        queryset = (
            PizzaPricing.objects.filter(pizza__is_active=True)
            .select_related("pizza")
            .order_by("pizza__name")
        )

        if not queryset.exists():
            self.stdout.write(self.style.WARNING("No active pizzas found."))
            return

        include_cost: bool = options["include_cost"]

        header_parts = [f"{'Pizza':<22}", f"{'Final Price':>14}"]
        if include_cost:
            header_parts.append(f"{'Ingredient Cost':>18}")
        header_parts.append("Flags")
        header = " ".join(header_parts)
        self.stdout.write(header)
        self.stdout.write("-" * len(header))

        for price in queryset:
            final_price = _format_money(price.final_price_with_vat)
            cost_price = _format_money(price.ingredient_cost)
            flags = _format_flags(
                price.is_vegetarian_computed, price.is_vegan_computed
            )

            line_parts = [f"{price.pizza.name:<22}", f"{final_price:>14}"]
            if include_cost:
                line_parts.append(f"{cost_price:>18}")
            line_parts.append(flags)
            self.stdout.write(" ".join(line_parts))


def _format_money(value: Decimal) -> str:
    return f"EUR {value.quantize(Decimal('0.01'))}"


def _format_flags(is_vegetarian: bool, is_vegan: bool) -> str:
    flags: list[str] = []
    if is_vegetarian:
        flags.append("Vegetarian")
    if is_vegan:
        flags.append("Vegan")
    return ", ".join(flags) if flags else "-"
