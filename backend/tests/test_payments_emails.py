"""
Tests for payments and emails.
"""
import pytest


@pytest.mark.integration
class TestPayments:

    def test_config_public(self, client):
        res = client.get("/api/payments/config")
        assert res.status_code == 200
        data = res.get_json()
        assert "key_id" in data
        assert "is_mock" in data

    def test_create_order_requires_auth(self, client):
        res = client.post("/api/payments/create-order", json={"plan": "growth"})
        assert res.status_code == 401

    def test_create_order_invalid_plan(self, client, auth_headers):
        res = client.post("/api/payments/create-order",
            json={"plan": "invalid"},
            headers=auth_headers)
        assert res.status_code == 400

    def test_create_order_free_plan(self, client, auth_headers):
        res = client.post("/api/payments/create-order",
            json={"plan": "free"},
            headers=auth_headers)
        assert res.status_code == 400

    def test_create_order_growth(self, client, auth_headers):
        res = client.post("/api/payments/create-order",
            json={"plan": "growth"},
            headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["amount"] == 1499
        assert "order_id" in data
        assert data["is_mock"] is True

    def test_verify_mock_payment(self, client, auth_headers):
        # Create order
        create = client.post("/api/payments/create-order",
            json={"plan": "starter"}, headers=auth_headers)
        order = create.get_json()

        # Verify
        res = client.post("/api/payments/verify", json={
            "razorpay_order_id": order["order_id"],
            "razorpay_payment_id": "pay_mock_test123",
            "razorpay_signature": "mock_sig",
        }, headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["plan"] == "starter"

    def test_history(self, client, auth_headers):
        res = client.get("/api/payments/history", headers=auth_headers)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)


@pytest.mark.integration
class TestEmails:

    def test_logs(self, client, auth_headers):
        res = client.get("/api/emails/logs", headers=auth_headers)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)

    def test_preferences_get(self, client, auth_headers):
        res = client.get("/api/emails/preferences", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "weekly_digest" in data

    def test_preferences_update(self, client, auth_headers):
        res = client.put("/api/emails/preferences",
            json={"weekly_digest": False},
            headers=auth_headers)
        assert res.status_code == 200

        # Verify
        get_res = client.get("/api/emails/preferences", headers=auth_headers)
        assert get_res.get_json()["weekly_digest"] is False

    def test_send_test_email(self, client, auth_headers):
        res = client.post("/api/emails/test", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["result"]["status"] in ("mock_sent", "sent")


@pytest.mark.integration
class TestOAuth:

    def test_start_invalid_platform(self, client, auth_headers):
        res = client.get("/api/oauth/invalid/start", headers=auth_headers)
        assert res.status_code == 400

    def test_start_zomato(self, client, auth_headers):
        res = client.get("/api/oauth/zomato/start", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "authorize_url" in data
        assert "state" in data
        assert data["platform"] == "zomato"

    def test_consent_invalid_state(self, client, auth_headers):
        res = client.post("/api/oauth/zomato/consent",
            json={"state": "invalid_state_xyz"},
            headers=auth_headers)
        assert res.status_code == 400

    def test_full_oauth_flow(self, client, auth_headers):
        # Start
        start = client.get("/api/oauth/swiggy/start", headers=auth_headers)
        state = start.get_json()["state"]

        # Consent (mock)
        res = client.post("/api/oauth/swiggy/consent",
            json={"state": state},
            headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["platform"] == "swiggy"
        assert data["integration_id"] > 0


@pytest.mark.integration
class TestTeam:

    def test_my_role(self, client, auth_headers):
        res = client.get("/api/team/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert data["role"] == "owner"

    def test_list_members(self, client, auth_headers):
        res = client.get("/api/team/", headers=auth_headers)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)


@pytest.mark.integration
class TestKitchens:

    def test_list(self, client, auth_headers):
        res = client.get("/api/kitchens/", headers=auth_headers)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)
        assert len(res.get_json()) >= 1

    def test_create(self, client, auth_headers):
        res = client.post("/api/kitchens/",
            json={"name": "Test Branch", "city": "Mumbai"},
            headers=auth_headers)
        assert res.status_code == 201
        assert res.get_json()["name"] == "Test Branch"
