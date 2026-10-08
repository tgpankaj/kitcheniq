"""
KitchenIQ — Plans & Subscription Routes
GET  /api/plans/              list all available plans
GET  /api/plans/current       current user's plan + usage
POST /api/plans/change        switch plan (mock for now)
GET  /api/plans/usage         current usage vs plan limits
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

from db.connection import execute_query, execute_one
from app.utils.auth import token_required
from app.utils.kitchen_context import get_current_kitchen_id


plans_bp = Blueprint('plans', __name__)


# ============================================================
# PLAN DEFINITIONS (hardcoded for now)
# ============================================================

PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price": 0,
        "price_yearly": 0,
        "popular": False,
        "limits": {
            "orders_per_month": 100,
            "kitchens": 1,
            "team_members": 1,
            "integrations": 0,
            "reports": True,
            "ai_insights": False,
        },
        "features": [
            "Up to 100 orders/month",
            "1 kitchen",
            "Basic dashboard",
            "CSV upload",
            "Basic analytics",
        ],
    },
    {
        "id": "starter",
        "name": "Starter",
        "price": 499,
        "price_yearly": 4990,
        "popular": False,
        "limits": {
            "orders_per_month": 1000,
            "kitchens": 1,
            "team_members": 3,
            "integrations": 1,
            "reports": True,
            "ai_insights": False,
        },
        "features": [
            "Up to 1,000 orders/month",
            "1 kitchen",
            "1 integration (Swiggy or Zomato)",
            "Full analytics",
            "Reports + CSV export",
            "Team: up to 3 members",
        ],
    },
    {
        "id": "growth",
        "name": "Growth",
        "price": 1499,
        "price_yearly": 14990,
        "popular": True,
        "limits": {
            "orders_per_month": 5000,
            "kitchens": 3,
            "team_members": 10,
            "integrations": 3,
            "reports": True,
            "ai_insights": True,
        },
        "features": [
            "Up to 5,000 orders/month",
            "3 kitchens (multi-branch)",
            "3 integrations",
            "AI insights & recommendations",
            "Food cost tracking",
            "Reports (Excel + PDF)",
            "Team: up to 10 members",
            "Priority support",
        ],
    },
    {
        "id": "pro",
        "name": "Pro",
        "price": 3999,
        "price_yearly": 39990,
        "popular": False,
        "limits": {
            "orders_per_month": -1,
            "kitchens": -1,
            "team_members": -1,
            "integrations": -1,
            "reports": True,
            "ai_insights": True,
        },
        "features": [
            "Unlimited orders",
            "Unlimited kitchens",
            "Unlimited integrations",
            "AI insights & forecasting",
            "Advanced reports (Excel, PDF, scheduled)",
            "Unlimited team members",
            "Custom domain",
            "24/7 priority support",
        ],
    },
]


def _plan_by_id(plan_id):
    for p in PLANS:
        if p["id"] == plan_id:
            return p
    return None


def _i(v):
    try:
        return int(v or 0)
    except (ValueError, TypeError):
        return 0


# ============================================================
# LIST
# ============================================================

@plans_bp.route('/', methods=['GET'])
def list_plans():
    """Public endpoint — no auth needed."""
    return jsonify(PLANS)


# ============================================================
# CURRENT
# ============================================================

@plans_bp.route('/current', methods=['GET'])
@token_required
def current():
    # Get current subscription
    sub = execute_one(
        """
        SELECT id, plan, status, started_at, expires_at
        FROM subscriptions
        WHERE user_id = %s AND status = 'active'
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (request.user_id,),
    )

    if sub:
        plan_id = sub['plan']
        started = sub['started_at']
        expires = sub['expires_at']
    else:
        # Default: free
        plan_id = 'free'
        started = None
        expires = None

    plan = _plan_by_id(plan_id) or PLANS[0]

    return jsonify({
        'plan': plan,
        'started_at': str(started) if started else None,
        'expires_at': str(expires) if expires else None,
        'status': sub['status'] if sub else 'active',
    })


# ============================================================
# USAGE
# ============================================================

@plans_bp.route('/usage', methods=['GET'])
@token_required
def usage():
    # Get plan
    sub = execute_one(
        "SELECT plan FROM subscriptions WHERE user_id = %s AND status = 'active' ORDER BY started_at DESC LIMIT 1",
        (request.user_id,),
    )
    plan_id = sub['plan'] if sub else 'free'
    plan = _plan_by_id(plan_id) or PLANS[0]

    kitchen_id = get_current_kitchen_id(request.user_id)

    # Orders this month
    orders_this_month = execute_one(
        """
        SELECT COUNT(*)::int AS c
        FROM orders
        WHERE kitchen_id = %s
          AND order_date >= DATE_TRUNC('month', CURRENT_DATE)
        """,
        (kitchen_id,),
    ) if kitchen_id else {'c': 0}

    # Kitchens count
    kitchens = execute_one(
        "SELECT COUNT(*)::int AS c FROM kitchens WHERE user_id = %s AND is_active = TRUE",
        (request.user_id,),
    )

    # Team members count
    team = execute_one(
        """
        SELECT COUNT(*)::int AS c
        FROM kitchen_users ku
        JOIN kitchens k ON k.id = ku.kitchen_id
        WHERE k.user_id = %s AND ku.is_active = TRUE
        """,
        (request.user_id,),
    )

    # Active integrations
    integrations = execute_one(
        """
        SELECT COUNT(*)::int AS c
        FROM integrations i
        JOIN kitchens k ON k.id = i.kitchen_id
        WHERE k.user_id = %s AND i.status = 'connected'
        """,
        (request.user_id,),
    )

    limits = plan['limits']

    def pct(used, limit):
        if limit == -1:
            return 100  # unlimited
        if limit <= 0:
            return 0
        return min(round(used / limit * 100, 1), 100)

    orders_used = _i(orders_this_month['c'])
    kitchens_used = _i(kitchens['c'])
    team_used = _i(team['c'])
    integrations_used = _i(integrations['c'])

    return jsonify({
        'plan_id': plan_id,
        'orders': {
            'used': orders_used,
            'limit': limits['orders_per_month'],
            'pct': pct(orders_used, limits['orders_per_month']),
        },
        'kitchens': {
            'used': kitchens_used,
            'limit': limits['kitchens'],
            'pct': pct(kitchens_used, limits['kitchens']),
        },
        'team_members': {
            'used': team_used,
            'limit': limits['team_members'],
            'pct': pct(team_used, limits['team_members']),
        },
        'integrations': {
            'used': integrations_used,
            'limit': limits['integrations'],
            'pct': pct(integrations_used, limits['integrations']),
        },
    })


# ============================================================
# CHANGE PLAN (Mock)
# ============================================================

@plans_bp.route('/change', methods=['POST'])
@token_required
def change_plan():
    d = request.get_json() or {}
    plan_id = (d.get('plan') or '').strip().lower()

    plan = _plan_by_id(plan_id)
    if not plan:
        return jsonify({'error': 'Invalid plan'}), 400

    # Deactivate existing
    execute_query(
        "UPDATE subscriptions SET status = 'cancelled' WHERE user_id = %s AND status = 'active'",
        (request.user_id,),
        fetch=False,
    )

    # Create new subscription
    started = datetime.utcnow()
    expires = started + timedelta(days=30)

    execute_query(
        """
        INSERT INTO subscriptions (user_id, plan, status, amount, started_at, expires_at)
        VALUES (%s, %s, 'active', %s, %s, %s)
        """,
        (request.user_id, plan_id, plan['price'], started, expires),
        fetch=False,
    )

    return jsonify({
        'message': f'Switched to {plan["name"]}',
        'plan_id': plan_id,
        'expires_at': expires.isoformat(),
    })
