"""
KitchenIQ — pytest fixtures
Central config for all tests.
"""
import os
import sys
from pathlib import Path
import pytest

# Add backend to path
BACKEND = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv
load_dotenv(BACKEND / ".env")


# ============================================================
# APP
# ============================================================

@pytest.fixture(scope="session")
def app():
    """Flask app for testing."""
    os.environ["FLASK_ENV"] = "testing"

    # Override DATABASE_URL with TEST_DATABASE_URL
    test_db = os.getenv("TEST_DATABASE_URL")
    if test_db:
        os.environ["DATABASE_URL"] = test_db
    else:
        # Fallback: use same DB (risky — will warn)
        print("\n⚠️  WARNING: TEST_DATABASE_URL not set. Using main DB (may pollute data)\n")

    # Reset db pool so it connects to test DB
    import db.connection as dbc
    dbc._pool = None

    from run import app as flask_app
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


# ============================================================
# AUTH
# ============================================================

@pytest.fixture
def unique_email():
    """Generate unique email for each test."""
    import time
    import secrets
    return f"test_{int(time.time())}_{secrets.token_hex(3)}@kitcheniq.test"


@pytest.fixture
def signup_user(client, unique_email):
    """Create a user via API and return token + user data."""
    res = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "test123456",
        "full_name": "Test User",
    })
    assert res.status_code == 201, f"Signup failed: {res.get_data(as_text=True)}"
    data = res.get_json()
    return {
        "token": data["token"],
        "user": data["user"],
        "kitchen": data["kitchen"],
        "email": unique_email,
        "password": "test123456",
    }


@pytest.fixture
def auth_headers(signup_user):
    """Authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {signup_user['token']}"}


# ============================================================
# FIXED USER (reusable across tests)
# ============================================================

@pytest.fixture
def known_user(client):
    """A known test user (created if not exists)."""
    email = "pytest_user@kitcheniq.test"
    password = "pytest123456"

    # Try login first
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    if res.status_code == 200:
        return res.get_json()

    # Create
    res = client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Pytest User",
    })
    if res.status_code == 201:
        return res.get_json()

    # If duplicate (race), login
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.get_json()


@pytest.fixture
def known_headers(known_user):
    return {"Authorization": f"Bearer {known_user['token']}"}
