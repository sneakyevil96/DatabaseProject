-- Week 4 Schema for Mamma Mia Pizza System
-- Run against PostgreSQL 15+ (tested with 17)

DO $$
BEGIN
    EXECUTE 'DROP VIEW IF EXISTS pizza_pricing CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_orderdiscountapplication CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_customerdiscountredemption CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_customerloyalty CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_deliveryzoneassignment CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_orderitem CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_customerorder CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_drink CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_dessert CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_dessertingredient CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_pizzaingredient CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_pizza CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_ingredient CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_customer CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_deliveryperson CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizzeria_discountcode CASCADE';
    EXECUTE 'DROP TYPE IF EXISTS order_status';
    EXECUTE 'DROP TYPE IF EXISTS delivery_type';
    EXECUTE 'DROP TYPE IF EXISTS order_item_type';
    EXECUTE 'DROP TYPE IF EXISTS discount_type';
END $$;

CREATE TYPE order_status AS ENUM ('pending', 'preparing', 'out_for_delivery', 'delivered', 'cancelled');
CREATE TYPE delivery_type AS ENUM ('delivery', 'pickup');
CREATE TYPE order_item_type AS ENUM ('pizza', 'drink', 'dessert');
CREATE TYPE discount_type AS ENUM ('percentage', 'fixed_amount');

CREATE TABLE pizzeria_ingredient (
    ingredient_id       SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL UNIQUE,
    is_meat             BOOLEAN NOT NULL DEFAULT FALSE,
    is_dairy            BOOLEAN NOT NULL DEFAULT FALSE,
    is_vegan            BOOLEAN NOT NULL DEFAULT FALSE,
    unit_cost           NUMERIC(10,2) NOT NULL CHECK (unit_cost > 0),
    unit_type           VARCHAR(20)  NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pizzeria_pizza (
    pizza_id            SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL UNIQUE,
    description         TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    is_vegetarian       BOOLEAN NOT NULL DEFAULT FALSE,
    is_vegan            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pizzeria_pizzaingredient (
    id                  SERIAL PRIMARY KEY,
    pizza_id            INTEGER NOT NULL REFERENCES pizzeria_pizza(pizza_id) ON DELETE CASCADE,
    ingredient_id       INTEGER NOT NULL REFERENCES pizzeria_ingredient(ingredient_id) ON DELETE RESTRICT,
    quantity            NUMERIC(10,2) NOT NULL CHECK (quantity > 0),
    position            SMALLINT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pizzaingredient_unique UNIQUE (pizza_id, ingredient_id)
);

CREATE TABLE pizzeria_customer (
    customer_id         SERIAL PRIMARY KEY,
    first_name          VARCHAR(50) NOT NULL,
    last_name           VARCHAR(50) NOT NULL,
    birthdate           DATE NOT NULL CHECK (birthdate <= CURRENT_DATE),
    email               VARCHAR(120) NOT NULL UNIQUE,
    phone               VARCHAR(30) NOT NULL,
    street              VARCHAR(150) NOT NULL,
    city                VARCHAR(80) NOT NULL,
    postal_code         VARCHAR(12) NOT NULL,
    country             VARCHAR(80) NOT NULL DEFAULT 'Belgium',
    gender              VARCHAR(20),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pizzeria_deliveryperson (
    delivery_person_id  SERIAL PRIMARY KEY,
    first_name          VARCHAR(50) NOT NULL,
    last_name           VARCHAR(50) NOT NULL,
    phone               VARCHAR(30) NOT NULL UNIQUE,
    postal_code         VARCHAR(12) NOT NULL,
    last_delivery_completed_at TIMESTAMPTZ,
    next_available_at   TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pizzeria_discountcode (
    discount_code_id    SERIAL PRIMARY KEY,
    code                VARCHAR(40) NOT NULL UNIQUE,
    description         TEXT,
    discount_type       discount_type NOT NULL,
    discount_value      NUMERIC(6,2) NOT NULL CHECK (discount_value > 0),
    valid_from          DATE NOT NULL,
    valid_until         DATE,
    is_one_time         BOOLEAN NOT NULL DEFAULT TRUE,
    usage_limit         INTEGER NOT NULL DEFAULT 1 CHECK (usage_limit > 0),
    used_count          INTEGER NOT NULL DEFAULT 0 CHECK (used_count >= 0),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pizzeria_drink (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL UNIQUE,
    category            VARCHAR(50) NOT NULL,
    price_eur           NUMERIC(6,2) NOT NULL CHECK (price_eur >= 0),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pizzeria_dessert (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL UNIQUE,
    description         TEXT,
    price_eur           NUMERIC(6,2) NOT NULL CHECK (price_eur >= 0),
    is_vegan            BOOLEAN NOT NULL DEFAULT FALSE,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pizzeria_dessertingredient (
    id                  SERIAL PRIMARY KEY,
    dessert_id          INTEGER NOT NULL REFERENCES pizzeria_dessert(id) ON DELETE CASCADE,
    ingredient          VARCHAR(100) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT dessertingredient_unique UNIQUE (dessert_id, ingredient)
);

CREATE TABLE pizzeria_customerloyalty (
    id                  SERIAL PRIMARY KEY,
    customer_id         INTEGER NOT NULL UNIQUE REFERENCES pizzeria_customer(customer_id) ON DELETE CASCADE,
    lifetime_pizzas     INTEGER NOT NULL DEFAULT 0,
    pizzas_since_last_reward INTEGER NOT NULL DEFAULT 0,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pizzeria_customerdiscountredemption (
    id                  SERIAL PRIMARY KEY,
    customer_id         INTEGER NOT NULL REFERENCES pizzeria_customer(customer_id) ON DELETE CASCADE,
    discount_code_id    INTEGER NOT NULL REFERENCES pizzeria_discountcode(discount_code_id) ON DELETE CASCADE,
    redeemed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT customerdiscount_unique UNIQUE (customer_id, discount_code_id)
);

CREATE TABLE pizzeria_deliveryzoneassignment (
    id                  SERIAL PRIMARY KEY,
    delivery_person_id  INTEGER NOT NULL REFERENCES pizzeria_deliveryperson(delivery_person_id) ON DELETE CASCADE,
    postal_code         VARCHAR(12) NOT NULL,
    priority            INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT deliveryzone_unique UNIQUE (delivery_person_id, postal_code)
);

CREATE TABLE pizzeria_customerorder (
    order_id            SERIAL PRIMARY KEY,
    customer_id         INTEGER NOT NULL REFERENCES pizzeria_customer(customer_id) ON DELETE CASCADE,
    order_datetime      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status              order_status NOT NULL DEFAULT 'pending',
    delivery_type       delivery_type NOT NULL DEFAULT 'delivery',
    subtotal_amount     NUMERIC(10,2) NOT NULL DEFAULT 0,
    discount_amount     NUMERIC(10,2) NOT NULL DEFAULT 0,
    total_due           NUMERIC(10,2) NOT NULL DEFAULT 0,
    loyalty_discount_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
    birthday_discount_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
    code_discount_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
    applied_discount_code_id INTEGER REFERENCES pizzeria_discountcode(discount_code_id) ON DELETE SET NULL,
    notes               TEXT,
    delivery_person_id  INTEGER REFERENCES pizzeria_deliveryperson(delivery_person_id) ON DELETE SET NULL,
    driver_assigned_at  TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pizzeria_orderitem (
    order_item_id       SERIAL PRIMARY KEY,
    order_id            INTEGER NOT NULL REFERENCES pizzeria_customerorder(order_id) ON DELETE CASCADE,
    item_type           order_item_type NOT NULL,
    pizza_id            INTEGER REFERENCES pizzeria_pizza(pizza_id) ON DELETE SET NULL,
    drink_id            INTEGER REFERENCES pizzeria_drink(id) ON DELETE SET NULL,
    dessert_id          INTEGER REFERENCES pizzeria_dessert(id) ON DELETE SET NULL,
    item_name_snapshot  VARCHAR(120) NOT NULL,
    quantity            INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    base_price          NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (base_price >= 0),
    unit_price_at_order NUMERIC(10,2) NOT NULL CHECK (unit_price_at_order >= 0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT orderitem_product_presence CHECK (
        (item_type = 'pizza' AND pizza_id IS NOT NULL AND drink_id IS NULL AND dessert_id IS NULL)
        OR (item_type = 'drink' AND drink_id IS NOT NULL AND pizza_id IS NULL AND dessert_id IS NULL)
        OR (item_type = 'dessert' AND dessert_id IS NOT NULL AND pizza_id IS NULL AND drink_id IS NULL)
    )
);

CREATE TABLE pizzeria_orderdiscountapplication (
    id                  SERIAL PRIMARY KEY,
    order_id            INTEGER NOT NULL REFERENCES pizzeria_customerorder(order_id) ON DELETE CASCADE,
    discount_code_id    INTEGER NOT NULL REFERENCES pizzeria_discountcode(discount_code_id) ON DELETE CASCADE,
    amount              NUMERIC(10,2) NOT NULL,
    applied_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE VIEW pizza_pricing AS
SELECT
    p.pizza_id,
    p.description,
    p.is_active,
    SUM(pi.quantity * i.unit_cost) AS ingredient_cost,
    ROUND(SUM(pi.quantity * i.unit_cost) * 1.40, 2) AS price_with_margin,
    ROUND(SUM(pi.quantity * i.unit_cost) * 1.40 * 1.09, 2) AS final_price_with_vat,
    BOOL_AND(NOT i.is_meat) AS is_vegetarian_computed,
    BOOL_AND(NOT i.is_meat AND NOT i.is_dairy) AS is_vegan_computed
FROM pizzeria_pizza p
JOIN pizzeria_pizzaingredient pi ON pi.pizza_id = p.pizza_id
JOIN pizzeria_ingredient i ON i.ingredient_id = pi.ingredient_id
GROUP BY p.pizza_id, p.description, p.is_active;
