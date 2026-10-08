"""
KitchenIQ — Food Cost Routes
GET    /api/foodcost/ingredients
POST   /api/foodcost/ingredients
PUT    /api/foodcost/ingredients/<id>
DELETE /api/foodcost/ingredients/<id>

GET    /api/foodcost/recipes
POST   /api/foodcost/recipes
DELETE /api/foodcost/recipes/<id>

GET    /api/foodcost/dish-costing   (real food cost per dish from recipes)
GET    /api/foodcost/summary        (KPIs)
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_query, execute_one
from app.utils.auth import token_required


foodcost_bp = Blueprint('foodcost', __name__)


def _f(v):
    try:
        return float(v or 0)
    except (ValueError, TypeError):
        return 0.0


def _i(v):
    try:
        return int(v or 0)
    except (ValueError, TypeError):
        return 0


def get_kitchen_id(user_id):
    from app.utils.kitchen_context import get_current_kitchen_id
    return get_current_kitchen_id(user_id)


# ============================================================
# INGREDIENTS
# ============================================================

@foodcost_bp.route('/ingredients', methods=['GET'])
@token_required
def list_ingredients():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    rows = execute_query(
        """
        SELECT id, name, unit, cost_per_unit, current_stock, reorder_threshold, is_active
        FROM ingredients
        WHERE kitchen_id = %s AND is_active = TRUE
        ORDER BY name
        """,
        (kitchen_id,),
    )

    return jsonify([
        {
            'id': r['id'],
            'name': r['name'],
            'unit': r['unit'],
            'cost_per_unit': round(_f(r['cost_per_unit']), 2),
            'current_stock': round(_f(r['current_stock']), 2),
            'reorder_threshold': round(_f(r['reorder_threshold']), 2),
            'low_stock': _f(r['current_stock']) <= _f(r['reorder_threshold']),
        }
        for r in rows
    ])


@foodcost_bp.route('/ingredients', methods=['POST'])
@token_required
def create_ingredient():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    d = request.get_json() or {}
    name = (d.get('name') or '').strip()
    unit = (d.get('unit') or 'kg').strip()
    cost = _f(d.get('cost_per_unit'))
    stock = _f(d.get('current_stock'))
    threshold = _f(d.get('reorder_threshold'))

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    existing = execute_one(
        "SELECT id FROM ingredients WHERE kitchen_id = %s AND name = %s",
        (kitchen_id, name),
    )
    if existing:
        return jsonify({'error': 'Ingredient already exists'}), 409

    row = execute_one(
        """
        INSERT INTO ingredients (kitchen_id, name, unit, cost_per_unit, current_stock, reorder_threshold)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, name
        """,
        (kitchen_id, name, unit, cost, stock, threshold),
    )

    return jsonify({'message': 'Ingredient created', 'id': row['id']}), 201


@foodcost_bp.route('/ingredients/<int:iid>', methods=['PUT'])
@token_required
def update_ingredient(iid):
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    existing = execute_one(
        "SELECT id FROM ingredients WHERE id = %s AND kitchen_id = %s",
        (iid, kitchen_id),
    )
    if not existing:
        return jsonify({'error': 'Ingredient not found'}), 404

    d = request.get_json() or {}

    execute_query(
        """
        UPDATE ingredients
        SET name = COALESCE(%s, name),
            unit = COALESCE(%s, unit),
            cost_per_unit = COALESCE(%s, cost_per_unit),
            current_stock = COALESCE(%s, current_stock),
            reorder_threshold = COALESCE(%s, reorder_threshold),
            updated_at = NOW()
        WHERE id = %s AND kitchen_id = %s
        """,
        (
            d.get('name'),
            d.get('unit'),
            _f(d.get('cost_per_unit')) if 'cost_per_unit' in d else None,
            _f(d.get('current_stock')) if 'current_stock' in d else None,
            _f(d.get('reorder_threshold')) if 'reorder_threshold' in d else None,
            iid,
            kitchen_id,
        ),
        fetch=False,
    )

    return jsonify({'message': 'Updated'})


@foodcost_bp.route('/ingredients/<int:iid>', methods=['DELETE'])
@token_required
def delete_ingredient(iid):
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    execute_query(
        "UPDATE ingredients SET is_active = FALSE WHERE id = %s AND kitchen_id = %s",
        (iid, kitchen_id),
        fetch=False,
    )

    return jsonify({'message': 'Deleted'})


# ============================================================
# RECIPES
# ============================================================

@foodcost_bp.route('/recipes', methods=['GET'])
@token_required
def list_recipes():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    dish = request.args.get('dish')

    if dish:
        rows = execute_query(
            """
            SELECT r.id, r.menu_item_name, r.quantity_required,
                   i.id AS ingredient_id, i.name AS ingredient_name,
                   i.unit, i.cost_per_unit
            FROM recipes r
            JOIN ingredients i ON i.id = r.ingredient_id
            WHERE r.kitchen_id = %s AND r.menu_item_name = %s
            ORDER BY i.name
            """,
            (kitchen_id, dish),
        )
    else:
        rows = execute_query(
            """
            SELECT r.id, r.menu_item_name, r.quantity_required,
                   i.id AS ingredient_id, i.name AS ingredient_name,
                   i.unit, i.cost_per_unit
            FROM recipes r
            JOIN ingredients i ON i.id = r.ingredient_id
            WHERE r.kitchen_id = %s
            ORDER BY r.menu_item_name, i.name
            """,
            (kitchen_id,),
        )

    return jsonify([
        {
            'id': r['id'],
            'dish': r['menu_item_name'],
            'ingredient_id': r['ingredient_id'],
            'ingredient_name': r['ingredient_name'],
            'unit': r['unit'],
            'quantity': round(_f(r['quantity_required']), 3),
            'cost_per_unit': round(_f(r['cost_per_unit']), 2),
            'line_cost': round(_f(r['quantity_required']) * _f(r['cost_per_unit']), 2),
        }
        for r in rows
    ])


@foodcost_bp.route('/recipes', methods=['POST'])
@token_required
def create_recipe():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    d = request.get_json() or {}
    dish = (d.get('dish') or '').strip()
    ingredient_id = _i(d.get('ingredient_id'))
    qty = _f(d.get('quantity'))

    if not dish or not ingredient_id or qty <= 0:
        return jsonify({'error': 'dish, ingredient_id, quantity required'}), 400

    # Verify ingredient belongs to kitchen
    ing = execute_one(
        "SELECT id FROM ingredients WHERE id = %s AND kitchen_id = %s",
        (ingredient_id, kitchen_id),
    )
    if not ing:
        return jsonify({'error': 'Ingredient not found'}), 404

    # Upsert
    row = execute_one(
        """
        INSERT INTO recipes (kitchen_id, menu_item_name, ingredient_id, quantity_required)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (kitchen_id, menu_item_name, ingredient_id)
        DO UPDATE SET quantity_required = EXCLUDED.quantity_required
        RETURNING id
        """,
        (kitchen_id, dish, ingredient_id, qty),
    )

    return jsonify({'message': 'Recipe saved', 'id': row['id']}), 201


@foodcost_bp.route('/recipes/<int:rid>', methods=['DELETE'])
@token_required
def delete_recipe(rid):
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    execute_query(
        "DELETE FROM recipes WHERE id = %s AND kitchen_id = %s",
        (rid, kitchen_id),
        fetch=False,
    )

    return jsonify({'message': 'Deleted'})


# ============================================================
# DISH COSTING (real food cost from recipes)
# ============================================================

@foodcost_bp.route('/dish-costing', methods=['GET'])
@token_required
def dish_costing():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    try:
        days = int(request.args.get('days', 30))
        if days not in (7, 30, 90, 365):
            days = 30
    except (ValueError, TypeError):
        days = 30

    # Revenue per dish from orders
    revenue_rows = execute_query(
        """
        SELECT
            oi.item_name AS name,
            COALESCE(SUM(oi.quantity), 0) AS qty,
            COALESCE(SUM(oi.line_total), 0) AS revenue,
            COALESCE(AVG(oi.unit_price), 0) AS avg_price
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE o.kitchen_id = %s
          AND o.status != 'cancelled'
          AND o.order_date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY oi.item_name
        HAVING SUM(oi.quantity) > 0
        ORDER BY revenue DESC
        """,
        (kitchen_id, days),
    )

    # Real recipe cost per dish
    cost_rows = execute_query(
        """
        SELECT
            r.menu_item_name AS name,
            COALESCE(SUM(r.quantity_required * i.cost_per_unit), 0) AS recipe_cost
        FROM recipes r
        JOIN ingredients i ON i.id = r.ingredient_id
        WHERE r.kitchen_id = %s
        GROUP BY r.menu_item_name
        """,
        (kitchen_id,),
    )
    cost_map = {r['name']: _f(r['recipe_cost']) for r in cost_rows}

    result = []
    for r in revenue_rows:
        revenue = _f(r['revenue'])
        qty = _i(r['qty'])
        recipe_cost_per_unit = cost_map.get(r['name'])
        has_recipe = r['name'] in cost_map

        total_food_cost = (recipe_cost_per_unit or 0) * qty
        profit = revenue - total_food_cost
        margin = (profit / revenue * 100) if revenue > 0 else 0

        result.append({
            'name': r['name'],
            'quantity': qty,
            'revenue': round(revenue, 2),
            'avg_price': round(_f(r['avg_price']), 2),
            'cost_per_unit': round(recipe_cost_per_unit, 2) if has_recipe else None,
            'food_cost': round(total_food_cost, 2),
            'profit': round(profit, 2),
            'margin_pct': round(margin, 1),
            'has_recipe': has_recipe,
        })

    return jsonify(result)


# ============================================================
# SUMMARY
# ============================================================

@foodcost_bp.route('/summary', methods=['GET'])
@token_required
def summary():
    kitchen_id = get_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    ing = execute_one(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(current_stock * cost_per_unit), 0) AS stock_value,
            COUNT(*) FILTER (WHERE current_stock <= reorder_threshold AND reorder_threshold > 0) AS low_stock
        FROM ingredients
        WHERE kitchen_id = %s AND is_active = TRUE
        """,
        (kitchen_id,),
    )

    rec = execute_one(
        "SELECT COUNT(DISTINCT menu_item_name) AS dishes FROM recipes WHERE kitchen_id = %s",
        (kitchen_id,),
    )

    total_dishes = execute_one(
        """
        SELECT COUNT(DISTINCT item_name) AS c
        FROM order_items oi
        JOIN orders o ON o.id = oi.order_id
        WHERE o.kitchen_id = %s AND o.status != 'cancelled'
        """,
        (kitchen_id,),
    )

    coverage = 0
    if total_dishes and _i(total_dishes['c']) > 0:
        coverage = round(_i(rec['dishes']) / _i(total_dishes['c']) * 100, 1)

    return jsonify({
        'total_ingredients': _i(ing['total']),
        'stock_value': round(_f(ing['stock_value']), 2),
        'low_stock_count': _i(ing['low_stock']),
        'dishes_with_recipes': _i(rec['dishes']),
        'recipe_coverage_pct': coverage,
    })