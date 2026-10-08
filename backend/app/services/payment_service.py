"""
KitchenIQ — Payment Service (Razorpay)
Handles order creation, signature verification, subscriptions.
"""
import os
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta

from dotenv import load_dotenv

from db.connection import execute_query, execute_one

load_dotenv()


def _is_mock():
    return os.getenv('RAZORPAY_MOCK_MODE', 'false').lower() == 'true'


def _get_client():
    """Return Razorpay client. Returns None in mock mode."""
    if _is_mock():
        return None

    try:
        import razorpay
        return razorpay.Client(
            auth=(os.getenv('RAZORPAY_KEY_ID'), os.getenv('RAZORPAY_KEY_SECRET'))
        )
    except Exception as e:
        print(f"[razorpay] client init failed: {e}")
        return None


# ============================================================
# ORDER CREATION
# ============================================================

def create_order(user_id, plan_id, amount, currency='INR'):
    """
    Create a Razorpay order (or mock order in mock mode).
    Returns: {order_id, amount, currency, key_id, is_mock}
    """

    # In mock mode, generate fake order id
    if _is_mock():
        mock_order_id = f"order_mock_{secrets.token_hex(8)}"

        # Save pending subscription
        _save_pending(user_id, plan_id, mock_order_id, amount)

        return {
            'order_id': mock_order_id,
            'amount': amount,
            'currency': currency,
            'key_id': 'rzp_test_mock_key_id',
            'is_mock': True,
        }

    # Real Razorpay
    client = _get_client()
    if not client:
        raise Exception("Razorpay client not configured")

    amount_paise = int(amount * 100)  # Razorpay expects paise

    try:
        order = client.order.create({
            'amount': amount_paise,
            'currency': currency,
            'receipt': f"kitcheniq_{user_id}_{int(datetime.now().timestamp())}",
            'notes': {
                'user_id': str(user_id),
                'plan_id': plan_id,
            },
        })

        _save_pending(user_id, plan_id, order['id'], amount)

        return {
            'order_id': order['id'],
            'amount': amount,
            'currency': currency,
            'key_id': os.getenv('RAZORPAY_KEY_ID'),
            'is_mock': False,
        }
    except Exception as e:
        print(f"[razorpay] order creation failed: {e}")
        raise


def _save_pending(user_id, plan_id, razorpay_order_id, amount):
    """Save pending subscription row."""
    # Cancel any previous 'pending' for this user
    execute_query(
        "UPDATE subscriptions SET status = 'cancelled' WHERE user_id = %s AND status = 'pending'",
        (user_id,),
        fetch=False,
    )

    execute_query(
        """
        INSERT INTO subscriptions (user_id, plan, status, amount, razorpay_order_id)
        VALUES (%s, %s, 'pending', %s, %s)
        """,
        (user_id, plan_id, amount, razorpay_order_id),
        fetch=False,
    )


# ============================================================
# SIGNATURE VERIFICATION
# ============================================================

def verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Verify Razorpay signature. In mock mode, always returns True.
    """
    if _is_mock():
        return True

    secret = os.getenv('RAZORPAY_KEY_SECRET')
    if not secret:
        return False

    msg = f"{razorpay_order_id}|{razorpay_payment_id}".encode()
    expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected, razorpay_signature)


# ============================================================
# SUBSCRIPTION ACTIVATION
# ============================================================

def activate_subscription(user_id, razorpay_order_id, razorpay_payment_id):
    """Activate subscription after successful payment."""

    # Find pending subscription
    sub = execute_one(
        """
        SELECT id, plan
        FROM subscriptions
        WHERE user_id = %s AND razorpay_order_id = %s
        ORDER BY id DESC LIMIT 1
        """,
        (user_id, razorpay_order_id),
    )

    if not sub:
        return None

    # Extend expiry by 30 days
    expires_at = datetime.utcnow() + timedelta(days=30)

    # Cancel other active
    execute_query(
        "UPDATE subscriptions SET status = 'cancelled' WHERE user_id = %s AND status = 'active' AND id != %s",
        (user_id, sub['id']),
        fetch=False,
    )

    # Activate this one
    execute_query(
        """
        UPDATE subscriptions
        SET status = 'active',
            razorpay_payment_id = %s,
            started_at = NOW(),
            expires_at = %s
        WHERE id = %s
        """,
        (razorpay_payment_id, expires_at, sub['id']),
        fetch=False,
    )

    return {
        'subscription_id': sub['id'],
        'plan': sub['plan'],
        'expires_at': expires_at.isoformat(),
    }


# ============================================================
# WEBHOOK SIGNATURE VERIFICATION
# ============================================================

def verify_webhook_signature(body_bytes, signature):
    """Verify Razorpay webhook signature."""
    if _is_mock():
        return True

    secret = os.getenv('RAZORPAY_WEBHOOK_SECRET')
    if not secret:
        return False

    expected = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


# ============================================================
# REFUND (for future use)
# ============================================================

def create_refund(payment_id, amount=None):
    """Issue a refund. Mock mode returns fake refund id."""
    if _is_mock():
        return {
            'id': f"rfnd_mock_{secrets.token_hex(6)}",
            'amount': amount,
            'status': 'processed',
        }

    client = _get_client()
    if not client:
        raise Exception("Razorpay client not configured")

    params = {'payment_id': payment_id}
    if amount:
        params['amount'] = int(amount * 100)

    return client.payment.refund(payment_id, params)
