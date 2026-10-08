-- ============================================================
-- KitchenIQ — Migration 002: Ingredients + Recipes
-- ============================================================

BEGIN;

CREATE TABLE IF NOT EXISTS ingredients (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    unit VARCHAR(50) NOT NULL DEFAULT 'kg',
    cost_per_unit NUMERIC(10, 2) NOT NULL DEFAULT 0,
    current_stock NUMERIC(10, 2) NOT NULL DEFAULT 0,
    reorder_threshold NUMERIC(10, 2) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(kitchen_id, name)
);

CREATE INDEX IF NOT EXISTS idx_ingredients_kitchen ON ingredients(kitchen_id);

CREATE TABLE IF NOT EXISTS recipes (
    id SERIAL PRIMARY KEY,
    kitchen_id INTEGER NOT NULL REFERENCES kitchens(id) ON DELETE CASCADE,
    menu_item_name VARCHAR(255) NOT NULL,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
    quantity_required NUMERIC(10, 3) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(kitchen_id, menu_item_name, ingredient_id)
);

CREATE INDEX IF NOT EXISTS idx_recipes_kitchen ON recipes(kitchen_id);
CREATE INDEX IF NOT EXISTS idx_recipes_menu_item ON recipes(kitchen_id, menu_item_name);

INSERT INTO schema_migrations (version)
VALUES ('002_ingredients_recipes')
ON CONFLICT (version) DO NOTHING;

COMMIT;

SELECT 'Migration 002 applied!' AS status;