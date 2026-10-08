"""
Tests for dashboard, analytics, and other core endpoints.
"""
import pytest


@pytest.mark.integration
class TestHealth:

    def test_health(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        assert res.get_json()["status"] == "ok"

    def test_root(self, client):
        res = client.get("/")
        assert res.status_code == 200

    def test_404_unknown_endpoint(self, client):
        res = client.get("/api/nonexistent")
        assert res.status_code == 404


@pytest.mark.integration
class TestDashboard:

    def test_summary_requires_auth(self, client):
        res = client.get("/api/dashboard/summary")
        assert res.status_code == 401

    def test_summary_with_auth(self, client, auth_headers):
        res = client.get("/api/dashboard/summary?days=7", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "kpis" in data
        assert "trend" in data
        assert "platforms" in data

    def test_summary_invalid_days(self, client, auth_headers):
        res = client.get("/api/dashboard/summary?days=999", headers=auth_headers)
        # Should fallback to default
        assert res.status_code == 200

    def test_recent_orders(self, client, auth_headers):
        res = client.get("/api/dashboard/recent-orders", headers=auth_headers)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)


@pytest.mark.integration
class TestAnalytics:

    def test_dishes(self, client, auth_headers):
        res = client.get("/api/analytics/dishes?days=7", headers=auth_headers)
        assert res.status_code == 200

    def test_peak_hours(self, client, auth_headers):
        res = client.get("/api/analytics/peak-hours?days=7", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 24  # 24 hours

    def test_cancellations(self, client, auth_headers):
        res = client.get("/api/analytics/cancellations?days=7", headers=auth_headers)
        assert res.status_code == 200


@pytest.mark.integration
class TestCustomers:

    def test_summary(self, client, auth_headers):
        res = client.get("/api/customers/summary?days=30", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "kpis" in data
        assert "segments" in data

    def test_list(self, client, auth_headers):
        res = client.get("/api/customers/?limit=10", headers=auth_headers)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)

    def test_cohorts(self, client, auth_headers):
        res = client.get("/api/customers/cohorts?months=3", headers=auth_headers)
        assert res.status_code == 200

    def test_clv(self, client, auth_headers):
        res = client.get("/api/customers/clv", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "avg_lifetime_value" in data

    def test_churn_risk(self, client, auth_headers):
        res = client.get("/api/customers/churn-risk", headers=auth_headers)
        assert res.status_code == 200


@pytest.mark.integration
class TestIntegrations:

    def test_list(self, client, auth_headers):
        res = client.get("/api/integrations/", headers=auth_headers)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)

    def test_connect_invalid_platform(self, client, auth_headers):
        res = client.post("/api/integrations/connect",
            json={"platform": "invalid_platform"},
            headers=auth_headers)
        assert res.status_code == 400

    def test_connect_zomato(self, client, auth_headers):
        res = client.post("/api/integrations/connect",
            json={"platform": "zomato"},
            headers=auth_headers)
        assert res.status_code in (200, 201)


@pytest.mark.integration
class TestInsights:

    def test_list(self, client, auth_headers):
        res = client.get("/api/insights/", headers=auth_headers)
        assert res.status_code == 200
        assert isinstance(res.get_json(), list)

    def test_summary(self, client, auth_headers):
        res = client.get("/api/insights/summary", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "total" in data
        assert "by_type" in data


@pytest.mark.integration
class TestNotifications:

    def test_list(self, client, auth_headers):
        res = client.get("/api/notifications/", headers=auth_headers)
        assert res.status_code == 200

    def test_unread_count(self, client, auth_headers):
        res = client.get("/api/notifications/unread-count", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "unread" in data


@pytest.mark.integration
class TestPlans:

    def test_list_public(self, client):
        res = client.get("/api/plans/")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 4  # Free, Starter, Growth, Pro

    def test_current_requires_auth(self, client):
        res = client.get("/api/plans/current")
        assert res.status_code == 401

    def test_current_with_auth(self, client, auth_headers):
        res = client.get("/api/plans/current", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "plan" in data

    def test_usage(self, client, auth_headers):
        res = client.get("/api/plans/usage", headers=auth_headers)
        assert res.status_code == 200
        data = res.get_json()
        assert "orders" in data
        assert "kitchens" in data
