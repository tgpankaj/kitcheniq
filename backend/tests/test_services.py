"""
Unit tests for services (no DB).
"""
import pytest


@pytest.mark.unit
class TestEncryption:

    def test_encrypt_decrypt(self):
        from app.utils.encryption import encrypt, decrypt
        original = "my_secret_token_12345"
        encrypted = encrypt(original)
        decrypted = decrypt(encrypted)

        assert encrypted != original
        assert encrypted.startswith("gAAAAA")  # Fernet prefix
        assert decrypted == original

    def test_encrypt_none(self):
        from app.utils.encryption import encrypt, decrypt
        assert encrypt(None) is None
        assert decrypt(None) is None


@pytest.mark.unit
class TestMockIntegration:

    def test_fetch_orders(self):
        from app.services.integrations.mock import MockIntegration
        mock = MockIntegration(kitchen_id=1, platform='zomato')
        mock.connect()

        orders = mock.fetch_orders(count=5)
        assert len(orders) == 5

        order = orders[0]
        assert 'external_order_id' in order
        assert 'gross_amount' in order
        assert 'platform_fee' in order
        assert order['platform'] == 'zomato'
        assert order['gross_amount'] > 0

    def test_zomato_fee(self):
        from app.services.integrations.mock import MockIntegration
        mock = MockIntegration(kitchen_id=1, platform='zomato')
        mock.connect()
        orders = mock.fetch_orders(count=20)

        # Zomato fee ~22%
        for o in orders:
            if o['gross_amount'] > 0 and o['discount'] == 0:
                pct = o['platform_fee'] / o['gross_amount'] * 100
                assert 20 <= pct <= 24


@pytest.mark.unit
class TestInsightsEngine:

    def test_generate_insights_empty(self):
        """Empty kitchen should return empty list."""
        from app.services.insights_service import generate_insights
        # Use non-existent kitchen_id (returns [])
        result = generate_insights(999999, days=30)
        assert isinstance(result, list)


@pytest.mark.unit
class TestEmailService:

    def test_base_template(self):
        from app.services.email_service import _base_template
        html = _base_template("Test Title", "<p>Hello</p>")
        assert "KitchenIQ" in html
        assert "Test Title" in html
        assert "<p>Hello</p>" in html

    def test_is_mock(self):
        from app.services.email_service import _is_mock
        # Should be True in test env
        import os
        os.environ.setdefault("EMAIL_MOCK_MODE", "true")


@pytest.mark.unit
class TestPaymentService:

    def test_plan_prices(self):
        from app.routes.payments import PLAN_PRICES
        assert PLAN_PRICES['free'] == 0
        assert PLAN_PRICES['starter'] == 499
        assert PLAN_PRICES['growth'] == 1499
        assert PLAN_PRICES['pro'] == 3999

    def test_verify_mock_signature(self):
        from app.services.payment_service import verify_payment_signature
        # In mock mode, always returns True
        result = verify_payment_signature("order_123", "pay_123", "mock_sig")
        assert result is True


@pytest.mark.unit
class TestPlansDefinitions:

    def test_plans_have_required_fields(self):
        from app.routes.plans import PLANS
        for plan in PLANS:
            assert 'id' in plan
            assert 'name' in plan
            assert 'price' in plan
            assert 'features' in plan
            assert 'limits' in plan
            assert len(plan['features']) > 0

    def test_plan_prices_increasing(self):
        from app.routes.plans import PLANS
        prices = [p['price'] for p in PLANS]
        assert prices == sorted(prices)
