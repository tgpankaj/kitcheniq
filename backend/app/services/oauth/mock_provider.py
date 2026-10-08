"""
KitchenIQ — Mock OAuth Provider
Simulates a real OAuth provider for testing.

Use this until we get real Swiggy/Zomato partner API access.
"""
import secrets
from datetime import datetime, timedelta

from app.services.oauth.base import BaseOAuthProvider


class MockOAuthProvider(BaseOAuthProvider):
    """Mock OAuth provider — behaves like real OAuth but auto-approves."""

    def __init__(self, kitchen_id, redirect_uri, platform='mock'):
        super().__init__(kitchen_id, redirect_uri)
        self.platform = platform

    @property
    def auth_url(self):
        # Frontend will redirect here; our mock consent page
        return "/pages/oauth-consent.html"

    def get_authorize_url(self, state):
        """Mock: return URL to our consent page (not external)."""
        return f"/pages/oauth-consent.html?state={state}&platform={self.platform}"

    def exchange_code_for_token(self, code):
        """Mock: any code returns a valid fake token."""
        return {
            'access_token': f"mock_access_{secrets.token_urlsafe(32)}",
            'refresh_token': f"mock_refresh_{secrets.token_urlsafe(32)}",
            'expires_in': 3600,
            'token_type': 'Bearer',
        }

    def fetch_user_info(self, access_token):
        return {
            'vendor_id': f"mock_vendor_{self.kitchen_id}",
            'name': f"Mock {self.platform.capitalize()} Vendor",
            'kitchen_id': self.kitchen_id,
        }


def get_provider(platform, kitchen_id, redirect_uri):
    """
    Factory — returns the right provider for the platform.

    Real providers (Swiggy, Zomato) will be added here when we get API access.
    """
    platform = (platform or '').lower()

    # For now, everything uses Mock
    # When real APIs are ready, add: if platform == 'swiggy': return SwiggyOAuthProvider(...)
    return MockOAuthProvider(kitchen_id, redirect_uri, platform=platform)
