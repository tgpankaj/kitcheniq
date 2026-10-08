"""
KitchenIQ — Kitchen Context Helper
Central place to determine "current kitchen" from request.
Priority:
1. X-Kitchen-Id header (if user owns it)
2. kitchen_id query param (if user owns it)
3. First kitchen of the user
"""
from flask import request
from db.connection import execute_one


def get_current_kitchen_id(user_id):
    """Return the current kitchen ID for this user's request."""
    # 1. Header
    header_id = request.headers.get('X-Kitchen-Id')
    if header_id:
        try:
            kid = int(header_id)
            k = execute_one(
                "SELECT id FROM kitchens WHERE id = %s AND user_id = %s AND is_active = TRUE",
                (kid, user_id),
            )
            if k:
                return k['id']
        except (ValueError, TypeError):
            pass

    # 2. Query param
    qparam = request.args.get('kitchen_id')
    if qparam:
        try:
            kid = int(qparam)
            k = execute_one(
                "SELECT id FROM kitchens WHERE id = %s AND user_id = %s AND is_active = TRUE",
                (kid, user_id),
            )
            if k:
                return k['id']
        except (ValueError, TypeError):
            pass

    # 3. First kitchen
    k = execute_one(
        "SELECT id FROM kitchens WHERE user_id = %s AND is_active = TRUE ORDER BY id LIMIT 1",
        (user_id,),
    )
    return k['id'] if k else None