"""
KitchenIQ — Mock Integration
Simulates Swiggy/Zomato with realistic random data.
"""
import random
from datetime import datetime, timedelta


DISHES = [
    ("Veg Biryani",           180.0, 85.0),
    ("Chicken Biryani",       260.0, 130.0),
    ("Paneer Butter Masala",  220.0, 95.0),
    ("Chicken Roll",          140.0, 60.0),
    ("Veg Hakka Noodles",     160.0, 55.0),
    ("Butter Chicken",        320.0, 150.0),
    ("Masala Dosa",           120.0, 40.0),
    ("Idli Sambar",            90.0, 30.0),
    ("Paneer Tikka",          240.0, 100.0),
    ("Dal Tadka",             160.0, 50.0),
]

FEE_PCT = {
    'zomato': 22.0,
    'swiggy': 25.0,
    'pos': 2.0,
    'website': 1.5,
}


class MockIntegration:
    """Generates realistic fake orders for testing."""

    def __init__(self, kitchen_id, platform='zomato', seed=None):
        self.kitchen_id = kitchen_id
        self.platform = platform.lower()
        self._rng = random.Random(seed or (kitchen_id * 1000 + hash(platform) % 100))

    def connect(self):
        return {
            'status': 'connected',
            'platform': self.platform,
            'auth_type': 'mock',
        }

    def test_connection(self):
        return True

    def fetch_orders(self, count=15):
        """Generate `count` realistic orders."""
        orders = []

        for i in range(count):
            # Random time in last 7 days
            days_ago = self._rng.randint(0, 6)
            hour = self._rng.choice([12, 13, 19, 20, 21, 22])
            minute = self._rng.randint(0, 59)
            order_dt = datetime.now() - timedelta(days=days_ago)
            order_dt = order_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # Pick 1-3 items
            num_items = self._rng.choices([1, 2, 3], weights=[60, 30, 10])[0]
            items = []
            gross = 0.0
            food_cost = 0.0

            for _ in range(num_items):
                dish = self._rng.choice(DISHES)
                qty = self._rng.choices([1, 2], weights=[80, 20])[0]
                items.append({
                    'name': dish[0],
                    'quantity': qty,
                    'unit_price': dish[1],
                    'food_cost': dish[2] * qty,
                })
                gross += dish[1] * qty
                food_cost += dish[2] * qty

            # Discount (10% of orders)
            discount = round(gross * 0.1, 2) if self._rng.random() < 0.1 else 0.0

            # Platform fee
            fee_pct = FEE_PCT.get(self.platform, 20.0)
            platform_fee = round((gross - discount) * fee_pct / 100, 2)

            # Tax (5% GST)
            tax = round((gross - discount) * 0.05, 2)

            # Packaging
            packaging = round(num_items * 10.0, 2)

            # Net revenue & profit
            net_revenue = round((gross - discount) - platform_fee - packaging, 2)
            profit = round(net_revenue - food_cost, 2)

            # Status (92% delivered)
            status = self._rng.choices(['delivered', 'cancelled'], weights=[92, 8])[0]

            orders.append({
                'external_order_id': f"{self.platform.upper()}-{order_dt.strftime('%Y%m%d%H%M')}-{i+1:03d}",
                'platform': self.platform,
                'order_date': order_dt.date(),
                'order_time': order_dt.time(),
                'customer_phone': f"9{self._rng.randint(100000000, 999999999)}",
                'customer_name': None,
                'items': items,
                'gross_amount': round(gross, 2),
                'discount': discount,
                'tax': tax,
                'platform_fee': platform_fee,
                'packaging_cost': packaging,
                'food_cost': round(food_cost, 2),
                'net_revenue': net_revenue,
                'profit': profit,
                'status': status,
            })

        return orders