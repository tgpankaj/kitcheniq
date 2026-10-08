"""
Tests for authentication endpoints.
"""
import pytest


@pytest.mark.integration
class TestAuth:

    def test_signup_success(self, client, unique_email):
        res = client.post("/api/auth/register", json={
            "email": unique_email,
            "password": "test123456",
            "full_name": "New User",
        })
        assert res.status_code == 201
        data = res.get_json()
        assert "token" in data
        assert data["user"]["email"] == unique_email
        assert data["kitchen"]["id"] > 0

    def test_signup_missing_email(self, client):
        res = client.post("/api/auth/register", json={
            "password": "test123456",
        })
        assert res.status_code == 400

    def test_signup_short_password(self, client, unique_email):
        res = client.post("/api/auth/register", json={
            "email": unique_email,
            "password": "123",
        })
        assert res.status_code == 400

    def test_signup_invalid_email(self, client):
        res = client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "test123456",
        })
        assert res.status_code == 400

    def test_signup_duplicate_email(self, client, signup_user):
        res = client.post("/api/auth/register", json={
            "email": signup_user["email"],
            "password": "otherpass",
        })
        assert res.status_code == 409

    def test_login_success(self, client, signup_user):
        res = client.post("/api/auth/login", json={
            "email": signup_user["email"],
            "password": signup_user["password"],
        })
        assert res.status_code == 200
        assert "token" in res.get_json()

    def test_login_wrong_password(self, client, signup_user):
        res = client.post("/api/auth/login", json={
            "email": signup_user["email"],
            "password": "wrong",
        })
        assert res.status_code == 401

    def test_login_unknown_email(self, client):
        res = client.post("/api/auth/login", json={
            "email": "nobody@nowhere.test",
            "password": "anything",
        })
        assert res.status_code == 401

    def test_me_with_valid_token(self, client, signup_user, auth_headers):
        res = client.get("/api/auth/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["email"] == signup_user["email"]

    def test_me_without_token(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_me_with_invalid_token(self, client):
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert res.status_code == 401
