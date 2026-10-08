"""
KitchenIQ — OAuth Routes
GET  /api/oauth/<platform>/start     initiate OAuth flow
GET  /api/oauth/<platform>/callback  handle provider redirect
POST /api/oauth/<platform>/consent   complete mock consent
"""
from flask import Blueprint, request, jsonify, redirect

from db.connection import execute_one
from app.utils.auth import token_required
from app.utils.kitchen_context import get_current_kitchen_id
from app.services.oauth.mock_provider import get_provider, MockOAuthProvider
from app.services.oauth.base import BaseOAuthProvider


oauth_bp = Blueprint('oauth', __name__)


SUPPORTED = ('zomato', 'swiggy', 'pos', 'website', 'mock')


@oauth_bp.route('/<platform>/start', methods=['GET'])
@token_required
def start(platform):
    """Initiate OAuth flow. Returns authorization URL."""
    kitchen_id = get_current_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    platform = platform.lower()
    if platform not in SUPPORTED:
        return jsonify({'error': f'Unsupported platform: {platform}'}), 400

    # Build redirect URI (this backend's callback)
    redirect_uri = request.host_url.rstrip('/') + f'/api/oauth/{platform}/callback'

    provider = get_provider(platform, kitchen_id, redirect_uri)
    state = provider.generate_state()

    authorize_url = provider.get_authorize_url(state)

    return jsonify({
        'authorize_url': authorize_url,
        'state': state,
        'platform': platform,
    })


@oauth_bp.route('/<platform>/callback', methods=['GET'])
def callback(platform):
    """Handle OAuth callback from provider."""
    platform = platform.lower()

    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')

    if error:
        return redirect(f"/pages/integrations.html?oauth_error={error}")

    if not code or not state:
        return redirect("/pages/integrations.html?oauth_error=missing_params")

    # Verify state
    state_row = BaseOAuthProvider.verify_state(state, platform)
    if not state_row:
        return redirect("/pages/integrations.html?oauth_error=invalid_state")

    kitchen_id = state_row['kitchen_id']

    # Exchange code for token
    redirect_uri = request.host_url.rstrip('/') + f'/api/oauth/{platform}/callback'
    provider = get_provider(platform, kitchen_id, redirect_uri)

    try:
        token_data = provider.exchange_code_for_token(code)
        provider.store_tokens(token_data)

        return redirect(f"/pages/integrations.html?oauth_success={platform}")
    except Exception as e:
        return redirect(f"/pages/integrations.html?oauth_error={str(e)[:100]}")


@oauth_bp.route('/<platform>/consent', methods=['POST'])
@token_required
def consent(platform):
    """Mock consent — simulates user approving OAuth on provider site."""
    kitchen_id = get_current_kitchen_id(request.user_id)
    if not kitchen_id:
        return jsonify({'error': 'No kitchen found'}), 404

    platform = platform.lower()
    d = request.get_json() or {}
    state = d.get('state')

    if not state:
        return jsonify({'error': 'state required'}), 400

    state_row = BaseOAuthProvider.verify_state(state, platform)
    if not state_row:
        return jsonify({'error': 'invalid_state'}), 400

    # Simulate successful OAuth
    redirect_uri = request.host_url.rstrip('/') + f'/api/oauth/{platform}/callback'
    provider = get_provider(platform, kitchen_id, redirect_uri)

    # Generate mock code and exchange
    mock_code = f"mock_code_{state[:8]}"
    token_data = provider.exchange_code_for_token(mock_code)
    integration_id = provider.store_tokens(token_data)

    return jsonify({
        'message': f'{platform.capitalize()} connected via OAuth',
        'platform': platform,
        'integration_id': integration_id,
    })
