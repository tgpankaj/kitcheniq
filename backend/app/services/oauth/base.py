"""
KitchenIQ — OAuth 2.0 Provider Base
Provider-agnostic OAuth flow for integrations.

Flow:
1. Frontend calls /api/oauth/<platform>/start
2. Backend generates state + redirect URL
3. User authorizes on provider site
4. Provider redirects to /api/oauth/<platform>/callback?code=...&state=...
5. Backend exchanges code for access_token
6. Encrypt and store token in integrations table
7. Redirect user to integrations page
"""
import secrets
import time
from abc import ABC, abstractmethod
from urllib.parse import urlencode

from db.connection import execute_query, execute_one
from app.utils.encryption import encrypt


class BaseOAuthProvider(ABC):
    """Abstract OAuth provider."""

    platform = None  # override in subclass
    auth_url = None
    token_url = None
    client_id = None
    client_secret = None
    scopes = []

    def __init__(self, kitchen_id, redirect_uri):
        self.kitchen_id = kitchen_id
        self.redirect_uri = redirect_uri

    # ---------- State management (CSRF protection) ----------

    def generate_state(self):
        """Generate + store OAuth state for CSRF protection."""
        state = secrets.token_urlsafe(32)

        # Store in DB with expiry (10 min)
        execute_query(
            """
            INSERT INTO oauth_states (state, kitchen_id, platform, created_at)
            VALUES (%s, %s, %s, NOW())
            """,
            (state, self.kitchen_id, self.platform),
            fetch=False,
        )

        return state

    @staticmethod
    def verify_state(state, platform):
        """Verify state is valid + not expired. Deletes it on success."""
        row = execute_one(
            """
            SELECT id, kitchen_id, platform
            FROM oauth_states
            WHERE state = %s
              AND platform = %s
              AND created_at >= NOW() - INTERVAL '10 minutes'
            """,
            (state, platform),
        )

        if not row:
            return None

        # Delete used state
        execute_query(
            "DELETE FROM oauth_states WHERE id = %s",
            (row['id'],),
            fetch=False,
        )

        return row

    # ---------- OAuth URLs ----------

    def get_authorize_url(self, state):
        """Return full authorization URL."""
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'state': state,
        }
        if self.scopes:
            params['scope'] = ' '.join(self.scopes)

        return f"{self.auth_url}?{urlencode(params)}"

    @abstractmethod
    def exchange_code_for_token(self, code):
        """Exchange authorization code for access_token.
        Must return dict: {access_token, refresh_token, expires_in, token_type}
        """
        pass

    @abstractmethod
    def fetch_user_info(self, access_token):
        """Fetch user/vendor info from provider. Returns dict."""
        pass

    # ---------- High-level flow ----------

    def store_tokens(self, token_data, user_info=None):
        """Encrypt + store tokens in integrations table."""
        access_enc = encrypt(token_data.get('access_token'))
        refresh_enc = encrypt(token_data.get('refresh_token'))

        expires_in = token_data.get('expires_in')  # seconds
        expires_at = None
        if expires_in:
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(seconds=int(expires_in))

        existing = execute_one(
            "SELECT id FROM integrations WHERE kitchen_id = %s AND platform = %s",
            (self.kitchen_id, self.platform),
        )

        if existing:
            execute_query(
                """
                UPDATE integrations
                SET status = 'connected',
                    auth_type = 'oauth',
                    access_token_encrypted = %s,
                    refresh_token_encrypted = %s,
                    token_expires_at = %s,
                    last_error = NULL,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (access_enc, refresh_enc, expires_at, existing['id']),
                fetch=False,
            )
            return existing['id']

        row = execute_one(
            """
            INSERT INTO integrations
                (kitchen_id, platform, status, auth_type,
                 access_token_encrypted, refresh_token_encrypted,
                 token_expires_at)
            VALUES (%s, %s, 'connected', 'oauth', %s, %s, %s)
            RETURNING id
            """,
            (self.kitchen_id, self.platform, access_enc, refresh_enc, expires_at),
        )
        return row['id']
