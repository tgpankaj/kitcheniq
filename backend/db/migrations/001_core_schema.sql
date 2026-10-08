-- ============================================================
-- KitchenIQ — Migration 001: Core Schema
-- Users, Kitchens, Menu Items, Orders, Customers
-- ============================================================

BEGIN;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'owner',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============================================================
-- KITCHENS
-- ============================================================
CREATE TABLE IF NOT EXISTS kitchens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    address TEXT,
    phone VARCHAR(20),
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    currency VARCHAR(10) DEFAULT 'INR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kitchens_user ON kitchens(user_id);

-- ============================================================
-- KITCHEN_USERS (Team members — future)
-- ============================================================
CREATE TABLE IF NOT EXISTS kitchen_users (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'staff',
    invited_at TIMESTAMP DEFAULT NOW(),
    accepted_at TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(kitchen_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_kitchen_users_kitchen ON kitchen_users(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_kitchen_users_user ON kitchen_users(user_id);

-- ============================================================
-- MENU_ITEMS (Dishes)
-- ============================================================
CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) DEFAULT 'Uncategorized',
    cost_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
    selling_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
    packaging_cost NUMERIC(10, 2) NOT NULL DEFAULT 0,
    prep_time_minutes INTEGER DEFAULT 15,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_menu_items_kitchen ON menu_items(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_menu_items_name ON menu_items(kitchen_id, name);

-- ============================================================
-- ORDERS (Header)
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,

    -- External reference (Swiggy/Zomato order ID)
    external_order_id VARCHAR(150),
    platform VARCHAR(50) NOT NULL DEFAULT 'manual',

    -- When
    order_date DATE NOT NULL,
    order_time TIME,

    -- Customer
    customer_phone VARCHAR(20),
    customer_name VARCHAR(255),

    -- Money (all in INR)
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    discount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    tax NUMERIC(10, 2) NOT NULL DEFAULT 0,
    platform_fee NUMERIC(10, 2) NOT NULL DEFAULT 0,
    delivery_fee NUMERIC(10, 2) NOT NULL DEFAULT 0,
    packaging_cost NUMERIC(10, 2) NOT NULL DEFAULT 0,
    food_cost NUMERIC(10, 2) NOT NULL DEFAULT 0,
    net_revenue NUMERIC(10, 2) NOT NULL DEFAULT 0,
    profit NUMERIC(10, 2) NOT NULL DEFAULT 0,

    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'delivered',
    cancelled_reason VARCHAR(255),

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_kitchen_date ON orders(kitchen_id, order_date DESC);
CREATE INDEX IF NOT EXISTS idx_orders_platform ON orders(kitchen_id, platform);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Unique dedup (external_order_id + platform + kitchen)
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_external_dedup
    ON orders(kitchen_id, platform, external_order_id)
    WHERE external_order_id IS NOT NULL;

-- ============================================================
-- ORDER_ITEMS (Line items)
-- ============================================================
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id INTEGER REFERENCES menu_items(id),
    item_name VARCHAR(255) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
    line_total NUMERIC(10, 2) NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_menu ON order_items(menu_item_id);

-- ============================================================
-- CUSTOMERS (Aggregated per phone)
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    phone VARCHAR(20) NOT NULL,
    name VARCHAR(255),
    first_order_date DATE,
    last_order_date DATE,
    total_orders INTEGER NOT NULL DEFAULT 0,
    total_spent NUMERIC(10, 2) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(kitchen_id, phone)
);

CREATE INDEX IF NOT EXISTS idx_customers_kitchen ON customers(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone);

-- ============================================================
-- Record migration
-- ============================================================
INSERT INTO schema_migrations (version)
VALUES ('001_core_schema')
ON CONFLICT (version) DO NOTHING;

COMMIT;

SELECT 'Migration 001 applied successfully!' AS status;