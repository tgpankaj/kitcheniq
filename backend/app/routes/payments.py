"""
KitchenIQ — Payment Routes (Razorpay)
POST /api/payments/create-order    create Razorpay order
POST /api/payments/verify          verify payment signature
POST /api/payments/webhook         Razorpay webhook handler
GET  /api/payments/history         user's payment history
GET  /api/payments/config          public config (key_id for frontend)
"""
from flask import Blueprint, request, jsonify, current_app
import os
import json

from db.connection import execute_query, execute_one
from app.utils.auth import token_required
from app.services import payment_service as ps
from app.services import email_service


payments_bp = Blueprint('payments', __name__)


# ============================================================
# PLAN PRICES
# ============================================================

PLAN_PRICES = {
    'free': 0,
    'starter': 499,
    'growth': 1499,
    'pro': 3999,
}


# ============================================================
# CONFIG (public)
# ============================================================

@payments_bp.route('/config', methods=['GET'])
def config():
    """Return public Razorpay config for frontend."""
    return jsonify({
        'key_id': os.getenv('RAZORPAY_KEY_ID', 'rzp_test_mock_key_id'),
        'is_mock': ps._is_mock(),
    })


# ============================================================
# CREATE ORDER
# ============================================================

@payments_bp.route('/create-order', methods=['POST'])
@token_required
def create_order():
    d = request.get_json() or {}
    plan_id = (d.get('plan') or '').strip().lower()

    if plan_id not in PLAN_PRICES:
        return jsonify({'error': 'Invalid plan'}), 400

    if plan_id == 'free':
        return jsonify({'error': 'Free plan does not require payment'}), 400

    amount = PLAN_PRICES[plan_id]

    try:
        order = ps.create_order(request.user_id, plan_id, amount)
        return jsonify(order)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# VERIFY PAYMENT
# ============================================================

@payments_bp.route('/verify', methods=['POST'])
@token_required
def verify():
    d = request.get_json() or {}

    order_id = d.get('razorpay_order_id')
    payment_id = d.get('razorpay_payment_id')
    signature = d.get('razorpay_signature')

    if not order_id or not payment_id:
        return jsonify({'error': 'Missing order_id or payment_id'}), 400

    # Verify signature
    valid = ps.verify_payment_signature(order_id, payment_id, signature or '')

    if not valid:
        # Log failed attempt
        _log_payment_event('payment_failed', order_id, payment_id, 'invalid_signature')
        return jsonify({'error': 'Invalid payment signature'}), 400

    # Activate subscription
    result = ps.activate_subscription(request.user_id, order_id, payment_id)

    if not result:
        return jsonify({'error': 'Subscription not found'}), 404

    _log_payment_event('payment_success', order_id, payment_id, f"plan={result['plan']}")

    # Send payment receipt email
    try:
        user = execute_one("SELECT email, full_name FROM users WHERE id = %s", (request.user_id,))
        if user:
            email_service.send_payment_receipt(
                user_id=request.user_id,
                email=user['email'],
                full_name=user['full_name'] or '',
                plan=result['plan'],
                amount=PLAN_PRICES.get(result['plan'], 0),
                expires_at=result['expires_at'][:10],
                payment_id=payment_id,
            )
    except Exception as e:
        print(f"[payment] receipt email failed: {e}")

    return jsonify({
        'message': 'Payment verified. Subscription activated!',
        'plan': result['plan'],
        'expires_at': result['expires_at'],
    })


# ============================================================
# WEBHOOK
# ============================================================

@payments_bp.route('/webhook', methods=['POST'])
def webhook():
    """Razorpay webhook — handles async events."""
    signature = request.headers.get('X-Razorpay-Signature', '')
    body = request.get_data()

    if not ps.verify_webhook_signature(body, signature):
        return jsonify({'error': 'Invalid signature'}), 400

    try:
        event = json.loads(body)
    except Exception:
        return jsonify({'error': 'Invalid JSON'}), 400

    event_type = event.get('event')
    payload = event.get('payload', {})

    # Handle events
    if event_type == 'payment.captured':
        payment = payload.get('payment', {}).get('entity', {})
        order_id = payment.get('order_id')
        payment_id = payment.get('id')
        notes = payment.get('notes', {})
        user_id = notes.get('user_id')

        if user_id and order_id:
            ps.activate_subscription(int(user_id), order_id, payment_id)

    elif event_type == 'payment.failed':
        payment = payload.get('payment', {}).get('entity', {})
        _log_payment_event('payment_failed', payment.get('order_id'), payment.get('id'), 'webhook')

    return jsonify({'ok': True})


# ============================================================
# HISTORY
# ============================================================

@payments_bp.route('/history', methods=['GET'])
@token_required
def history():
    rows = execute_query(
        """
        SELECT
            id, plan, status, amount, razorpay_order_id, razorpay_payment_id,
            started_at, expires_at, created_at
        FROM subscriptions
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 50
        """,
        (request.user_id,),
    )

    return jsonify([
        {
            'id': r['id'],
            'plan': r['plan'],
            'status': r['status'],
            'amount': float(r['amount']) if r['amount'] else 0,
            'order_id': r['razorpay_order_id'],
            'payment_id': r['razorpay_payment_id'],
            'started_at': str(r['started_at']) if r['started_at'] else None,
            'expires_at': str(r['expires_at']) if r['expires_at'] else None,
            'created_at': str(r['created_at']) if r['created_at'] else None,
        }
        for r in rows
    ])


# ============================================================
# HELPER
# ============================================================

def _log_payment_event(event, order_id, payment_id, extra):
    """Log payment events via audit service."""
    try:
        from app.services import audit_service
        audit_service.log_action(
            user_id=None,
            kitchen_id=None,
            action=event,
            category='payment',
            resource='subscription',
            resource_id=order_id,
            description=f"{event}: {extra}",
        )
    except Exception:
        pass
