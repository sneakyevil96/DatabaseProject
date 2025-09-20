"""Simple console helper to fetch menu pricing from PostgreSQL."""

import os
from decimal import Decimal

import psycopg


DSN = {
    "dbname": os.getenv("PGDATABASE", "mammamia_db"),
    "user": os.getenv("PGUSER", "mammamia_user"),
    "password": os.getenv("PGPASSWORD", "root!"),
    "host": os.getenv("PGHOST", "localhost"),
    "port": os.getenv("PGPORT", "5432"),
}


def format_euro(amount: Decimal) -> str:
    return f"EUR {amount.quantize(Decimal('0.01'))}"


def fetch_menu() -> list[tuple[str, Decimal, Decimal, bool, bool]]:
    query = (
        "SELECT pz.name, pp.ingredient_cost, pp.final_price_with_vat, "
        "pp.is_vegetarian_computed, pp.is_vegan_computed "
        "FROM pizza_pricing pp "
        "JOIN pizzeria_pizza pz ON pp.pizza_id = pz.id "
        "WHERE pz.is_active = TRUE "
        "ORDER BY pz.name"
    )
    with psycopg.connect(**DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()


def main() -> None:
    print("Mamma Mia Menu")
    print("-" * 40)
    try:
        rows = fetch_menu()
    except psycopg.Error as exc:  # pragma: no cover - diagnostic output
        print("Failed to fetch menu:", exc)
        return

    for name, cost, price, is_veg, is_vegan in rows:
        flags: list[str] = []
        if is_veg:
            flags.append("Vegetarian")
        if is_vegan:
            flags.append("Vegan")
        label = f" ({', '.join(flags)})" if flags else ""
        print(f"{name}{label}\n  Cost: {format_euro(cost)} -> Final price: {format_euro(price)}\n")


if __name__ == "__main__":
    main()

