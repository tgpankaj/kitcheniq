"""
KitchenIQ — Email Routes
GET  /api/emails/logs         email log history
GET  /api/emails/preferences  get user's email prefs
PUT  /api/emails/preferences  update prefs
POST /api/emails/test         send test email
"""
from flask import Blueprint, request, jsonify

from db.connection import execute_query, execute_one
from app.utils.auth import token_required
from app.services import email_service


emails_bp = Blueprint('emails', __name__)


# ============================================================
# LOGS
# ============================================================

@emails_bp.route('/logs', methods=['GET'])
@token_required
def logs():
    limit = min(int(request.args.get('limit', 50)), 200)

    rows = execute_query(
        """
        SELECT id, to_email, subject, template, status, error_message, sent_at
        FROM email_logs
        WHERE user_id = %s
        ORDER BY sent_at DESC
        LIMIT %s
        """,
        (request.user_id, limit),
    )

    return jsonify([
        {
            'id': r['id'],
            'to': r['to_email'],
            'subject': r['subject'],
            'template': r['template'],
            'status': r['status'],
            'error': r['error_message'],
            'sent_at': str(r['sent_at']) if r['sent_at'] else None,
        }
        for r in rows
    ])


# ============================================================
# PREFERENCES
# ============================================================

@emails_bp.route('/preferences', methods=['GET'])
@token_required
def get_prefs():
    pref = execute_one(
        "SELECT * FROM email_preferences WHERE user_id = %s",
        (request.user_id,),
    )

    if not pref:
        # Create default prefs
        execute_query(
            "INSERT INTO email_preferences (user_id) VALUES (%s)",
            (request.user_id,),
            fetch=False,
        )
        return jsonify({
            'welcome_email': True,
            'payment_receipts': True,
            'weekly_digest': True,
            'sync_alerts': True,
            'marketing': False,
        })

    return jsonify({
        'welcome_email': pref['welcome_email'],
        'payment_receipts': pref['payment_receipts'],
        'weekly_digest': pref['weekly_digest'],
        'sync_alerts': pref['sync_alerts'],
        'marketing': pref['marketing'],
    })


@emails_bp.route('/preferences', methods=['PUT'])
@token_required
def update_prefs():
    d = request.get_json() or {}

    # Ensure row exists
    execute_query(
        """
        INSERT INTO email_preferences (user_id) VALUES (%s)
        ON CONFLICT (user_id) DO NOTHING
        """,
        (request.user_id,),
        fetch=False,
    )

    execute_query(
        """
        UPDATE email_preferences
        SET welcome_email = COALESCE(%s, welcome_email),
            payment_receipts = COALESCE(%s, payment_receipts),
            weekly_digest = COALESCE(%s, weekly_digest),
            sync_alerts = COALESCE(%s, sync_alerts),
            marketing = COALESCE(%s, marketing),
            updated_at = NOW()
        WHERE user_id = %s
        """,
        (
            d.get('welcome_email'),
            d.get('payment_receipts'),
            d.get('weekly_digest'),
            d.get('sync_alerts'),
            d.get('marketing'),
            request.user_id,
        ),
        fetch=False,
    )

    return jsonify({'message': 'Preferences updated'})


# ============================================================
# TEST
# ============================================================

@emails_bp.route('/test', methods=['POST'])
@token_required
def test_email():
    user = execute_one(
        "SELECT email, full_name FROM users WHERE id = %s",
        (request.user_id,),
    )
    if not user:
        return jsonify({'error': 'User not found'}), 404

    result = email_service.send_welcome_email(
        request.user_id,
        user['email'],
        user['full_name'] or 'Test User',
    )

    return jsonify({
        'message': 'Test email triggered',
        'result': result,
    })
