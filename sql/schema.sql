-- Week 2 Schema for Mamma Mia Pizza System
-- Run against PostgreSQL 15+ (tested with 17)

-- Clean up existing types/tables when re-running in dev
DO $$
BEGIN
    EXECUTE 'DROP VIEW IF EXISTS pizza_pricing CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS order_item CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS customer_order CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizza_ingredient CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS pizza CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS ingredient CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS customer CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS delivery_person CASCADE';
    EXECUTE 'DROP TABLE IF EXISTS discount_code CASCADE';
    EXECUTE 'DROP TYPE IF EXISTS order_status';
    EXECUTE 'DROP TYPE IF EXISTS delivery_type';
    EXECUTE 'DROP TYPE IF EXISTS order_item_type';
    EXECUTE 'DROP TYPE IF EXISTS discount_type';
END $$;

CREATE TYPE order_status AS ENUM (
    'pending',
    'preparing',
    'out_for_delivery',
    'delivered',
    'cancelled'
);

CREATE TYPE delivery_type AS ENUM (
    'delivery',
    'pickup'
);

CREATE TYPE order_item_type AS ENUM (
    'pizza',
    'drink',
    'dessert'
);

CREATE TYPE discount_type AS ENUM (
    'percentage',
    'fixed_amount'
);

CREATE TABLE ingredient (
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

CREATE TABLE pizza (
    pizza_id            SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL UNIQUE,
    description         TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    is_vegetarian       BOOLEAN NOT NULL DEFAULT FALSE,
    is_vegan            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pizza_ingredient (
    pizza_ingredient_id SERIAL PRIMARY KEY,
    pizza_id            INTEGER NOT NULL REFERENCES pizza(pizza_id) ON DELETE CASCADE,
    ingredient_id       INTEGER NOT NULL REFERENCES ingredient(ingredient_id) ON DELETE RESTRICT,
    quantity            NUMERIC(10,2) NOT NULL CHECK (quantity > 0),
    position            SMALLINT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pizza_ingredient_unique UNIQUE (pizza_id, ingredient_id)
);

CREATE TABLE customer (
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

CREATE TABLE delivery_person (
    delivery_person_id  SERIAL PRIMARY KEY,
    first_name          VARCHAR(50) NOT NULL,
    last_name           VARCHAR(50) NOT NULL,
    phone               VARCHAR(30) NOT NULL UNIQUE,
    postal_code         VARCHAR(12) NOT NULL,
    last_delivery_completed_at TIMESTAMPTZ,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE discount_code (
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

CREATE TABLE customer_order (
    order_id            SERIAL PRIMARY KEY,
    customer_id         INTEGER NOT NULL REFERENCES customer(customer_id) ON DELETE CASCADE,
    order_datetime      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status              order_status NOT NULL DEFAULT 'pending',
    delivery_type       delivery_type NOT NULL DEFAULT 'delivery',
    total_discount      NUMERIC(10,2) NOT NULL DEFAULT 0,
    notes               TEXT,
    delivery_person_id  INTEGER REFERENCES delivery_person(delivery_person_id) ON DELETE SET NULL,
    driver_assigned_at  TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE order_item (
    order_item_id       SERIAL PRIMARY KEY,
    order_id            INTEGER NOT NULL REFERENCES customer_order(order_id) ON DELETE CASCADE,
    item_type           order_item_type NOT NULL,
    pizza_id            INTEGER REFERENCES pizza(pizza_id) ON DELETE SET NULL,
    item_name_snapshot  VARCHAR(120) NOT NULL,
    quantity            INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price_at_order NUMERIC(10,2) NOT NULL CHECK (unit_price_at_order >= 0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT order_item_requires_pizza
        CHECK (
            (item_type = 'pizza' AND pizza_id IS NOT NULL)
            OR (item_type <> 'pizza' AND pizza_id IS NULL)
        )
);

-- Derived view: calculates dynamic pricing per pizza
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
FROM pizza p
JOIN pizza_ingredient pi ON pi.pizza_id = p.pizza_id
JOIN ingredient i ON i.ingredient_id = pi.ingredient_id
GROUP BY p.pizza_id, p.description, p.is_active;


