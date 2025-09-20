"""Load sample data from CSV files into the database."""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from datetime import date
from pathlib import Path
from typing import Iterable

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from pizzeria import models


class Command(BaseCommand):
    help = "Load pizzas, ingredients, drinks, desserts, customers, and delivery people from CSV files."

    def add_arguments(self, parser):
        default_dir = Path(settings.BASE_DIR) / "pizzeria" / "templates" / "pizzeria"
        parser.add_argument(
            "--data-dir",
            type=Path,
            default=default_dir,
            help=f"Directory containing CSV files (default: {default_dir})",
        )
        parser.add_argument(
            "--purge",
            action="store_true",
            help="Remove existing menu/customer data before loading.",
        )

    def handle(self, *args, **options):
        data_dir: Path = options["data_dir"]
        if not data_dir.exists():
            raise CommandError(f"Data directory {data_dir} does not exist")

        with transaction.atomic():
            if options["purge"]:
                self._purge_existing_data()

            self.stdout.write(self.style.MIGRATE_HEADING("Loading ingredients"))
            self._load_ingredients(data_dir / "pizza_ingredients.csv")

            self.stdout.write(self.style.MIGRATE_HEADING("Loading pizzas"))
            self._load_pizzas(data_dir / "pizzas.csv")

            self.stdout.write(self.style.MIGRATE_HEADING("Linking pizza ingredients"))
            self._load_pizza_recipes(data_dir / "pizza_recipes.csv")

            self.stdout.write(self.style.MIGRATE_HEADING("Loading drinks"))
            self._load_drinks(data_dir / "drinks.csv")

            self.stdout.write(self.style.MIGRATE_HEADING("Loading desserts"))
            self._load_desserts(data_dir / "desserts.csv")

            self.stdout.write(self.style.MIGRATE_HEADING("Loading customers"))
            self._load_customers(data_dir / "customers_data.csv")

            self.stdout.write(self.style.MIGRATE_HEADING("Loading delivery personnel"))
            self._load_delivery_people(data_dir / "deliveryguy_data.csv")

        self.stdout.write(self.style.SUCCESS("Sample data loaded successfully."))

    def _purge_existing_data(self) -> None:
        tables = [
            models.OrderItem._meta.db_table,
            models.CustomerOrder._meta.db_table,
            models.PizzaIngredient._meta.db_table,
            models.Pizza._meta.db_table,
            models.Ingredient._meta.db_table,
            models.Drink._meta.db_table,
            models.DessertIngredient._meta.db_table,
            models.Dessert._meta.db_table,
            models.Customer._meta.db_table,
            models.DeliveryPerson._meta.db_table,
        ]
        quoted_tables = ", ".join(connection.ops.quote_name(table) for table in tables)
        with connection.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE;")

    def _load_ingredients(self, path: Path) -> None:
        rows = self._read_csv(path)
        for row in rows:
            category = row["category"].strip().lower()
            is_meat = category == "meat"
            is_dairy = category in {"cheese", "dairy"}
            models.Ingredient.objects.update_or_create(
                id=int(row["ingredient_id"]),
                defaults={
                    "name": row["ingredient_name"].strip(),
                    "is_meat": is_meat,
                    "is_dairy": is_dairy,
                    "is_vegan": self._to_bool(row.get("is_vegan")),
                    "unit_cost": self._to_decimal(row.get("unit_cost_eur")),
                    "unit_type": row.get("unit_measure", "gram").strip(),
                },
            )

    def _load_pizzas(self, path: Path) -> None:
        rows = self._read_csv(path)
        for row in rows:
            models.Pizza.objects.update_or_create(
                id=int(row["pizza_id"]),
                defaults={
                    "name": row["pizza_name"].strip(),
                    "description": row.get("description", "").strip(),
                    "is_active": str(row.get("is_active", "1")).strip() in {"1", "true", "True"},
                    "is_vegetarian": self._to_bool(row.get("is_vegetarian")),
                    "is_vegan": self._to_bool(row.get("is_vegan")),
                },
            )

    def _load_pizza_recipes(self, path: Path) -> None:
        models.PizzaIngredient.objects.all().delete()
        rows = self._read_csv(path)
        position_tracker: dict[int, int] = {}
        pizzas = {p.id: p for p in models.Pizza.objects.all()}
        ingredients = {i.id: i for i in models.Ingredient.objects.all()}
        to_create: list[models.PizzaIngredient] = []
        for row in rows:
            pizza_id = int(row["pizza_id"])
            ingredient_id = int(row["ingredient_id"])
            pizza = pizzas.get(pizza_id)
            ingredient = ingredients.get(ingredient_id)
            if not pizza or not ingredient:
                continue
            position_tracker[pizza_id] = position_tracker.get(pizza_id, 0) + 1
            to_create.append(
                models.PizzaIngredient(
                    pizza=pizza,
                    ingredient=ingredient,
                    quantity=self._to_decimal(row.get("quantity")),
                    position=position_tracker[pizza_id],
                )
            )
        models.PizzaIngredient.objects.bulk_create(to_create, batch_size=500)

    def _load_drinks(self, path: Path) -> None:
        rows = self._read_csv(path)
        for row in rows:
            models.Drink.objects.update_or_create(
                id=int(row["drink_id"]),
                defaults={
                    "name": row["drink_name"].strip(),
                    "category": row.get("category", "").strip(),
                    "price_eur": self._to_decimal(row.get("price_eur")),
                    "is_active": True,
                },
            )

    def _load_desserts(self, path: Path) -> None:
        rows = self._read_csv(path)
        models.DessertIngredient.objects.all().delete()
        for row in rows:
            dessert, _ = models.Dessert.objects.update_or_create(
                id=int(row["dessert_id"]),
                defaults={
                    "name": row["dessert_name"].strip(),
                    "description": row.get("description", "").strip(),
                    "price_eur": self._to_decimal(row.get("price_eur")),
                    "is_vegan": self._to_bool(row.get("is_vegan")),
                    "is_active": True,
                },
            )
            ingredients = [item.strip() for item in row.get("ingredients", "").split("|") if item.strip()]
            models.DessertIngredient.objects.bulk_create(
                [models.DessertIngredient(dessert=dessert, ingredient=name) for name in ingredients],
                ignore_conflicts=True,
            )

    def _load_customers(self, path: Path) -> None:
        rows = self._read_csv(path)
        for row in rows:
            models.Customer.objects.update_or_create(
                id=int(row["customer_id"]),
                defaults={
                    "first_name": row["first_name"].strip(),
                    "last_name": row["last_name"].strip(),
                    "email": row["email"].strip(),
                    "phone": row.get("phone", "").strip(),
                    "street": row.get("street", "").strip(),
                    "city": row.get("city", "").strip(),
                    "postal_code": row.get("postal_code", "").strip(),
                    "country": row.get("country", "Belgium").strip(),
                    "birthdate": self._parse_date(row.get("birthdate")),
                    "gender": row.get("gender", "").strip(),
                },
            )

    def _load_delivery_people(self, path: Path) -> None:
        rows = self._read_csv(path)
        for row in rows:
            postal_codes = [code.strip() for code in row.get("assigned_postcodes", "").split("|") if code.strip()]
            primary_postal = postal_codes[0] if postal_codes else ""
            models.DeliveryPerson.objects.update_or_create(
                id=int(row["deliveryguy_id"]),
                defaults={
                    "first_name": row["name"].strip(),
                    "last_name": row["surname"].strip(),
                    "phone": row.get("phone", "").strip(),
                    "postal_code": primary_postal,
                    "is_active": True,
                },
            )

    def _read_csv(self, path: Path) -> Iterable[dict[str, str]]:
        if not path.exists():
            raise CommandError(f"CSV file not found: {path}")
        with path.open("r", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            return list(reader)

    @staticmethod
    def _to_bool(value: str | None) -> bool:
        return str(value).strip() in {"1", "true", "True", "yes", "Yes"}

    @staticmethod
    def _to_decimal(value: str | None):
        if value in (None, ""):
            return Decimal("0")
        try:
            return Decimal(str(value).strip())
        except InvalidOperation as exc:
            raise CommandError(f"Cannot convert {value!r} to decimal") from exc

    @staticmethod
    def _parse_date(value: str | None) -> date:
        if not value:
            return date.today()
        return date.fromisoformat(value)




