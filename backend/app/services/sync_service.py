"""
KitchenIQ — Sync Service
Persists mock integration data into PostgreSQL.
Handles deduplication and logging.
"""
from datetime import datetime


from app.services import notification_service as notif
from app.services import email_service


class SyncService:

    def __init__(self, integration_id, kitchen_id, platform):
        self.integration_id = integration_id
        self.kitchen_id = kitchen_id
        self.platform = platform
        self.log_id = None
        self.stats = {'fetched': 0, 'created': 0, 'updated': 0, 'failed': 0}

    # ---------- Logging ----------

    def start_log(self):
        row = execute_one(
            """
            INSERT INTO sync_logs (integration_id, kitchen_id, status, started_at)
            VALUES (%s, %s, 'running', NOW())
            RETURNING id
            """,
            (self.integration_id, self.kitchen_id),
        )
        self.log_id = row['id'] if row else None

    def finish_log(self, status='success', error_message=None, duration=None):
        if not self.log_id:
            return
        execute_query(
            """
            UPDATE sync_logs
            SET status = %s, completed_at = NOW(),
                records_fetched = %s, records_created = %s,
                records_updated = %s, records_failed = %s,
                error_message = %s, duration_seconds = %s
            WHERE id = %s
            """,
            (
                status,
                self.stats['fetched'],
                self.stats['created'],
                self.stats['updated'],
                self.stats['failed'],
                error_message,
                duration,
                self.log_id,
            ),
            fetch=False,
        )

    # ---------- Order upsert ----------

    def upsert_order(self, order):
        """Return 'created' | 'updated' | 'failed'."""

        # Dedup check
        existing = execute_one(
            """
            SELECT id FROM orders
            WHERE kitchen_id = %s AND platform = %s AND external_order_id = %s
            """,
            (self.kitchen_id, order['platform'], order['external_order_id']),
        )

        if existing:
            execute_query(
                "UPDATE orders SET status = %s, updated_at = NOW() WHERE id = %s",
                (order['status'], existing['id']),
                fetch=False,
            )
            return 'updated'

        row = execute_one(
            """
            INSERT INTO orders (
                kitchen_id, external_order_id, platform,
                order_date, order_time, customer_phone, customer_name,
                total_amount, discount, tax, platform_fee,
                packaging_cost, food_cost, net_revenue, profit, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                self.kitchen_id, order['external_order_id'], order['platform'],
                order['order_date'], order['order_time'],
                order.get('customer_phone'), order.get('customer_name'),
                order['gross_amount'], order['discount'], order['tax'],
                order['platform_fee'], order['packaging_cost'], order['food_cost'],
                order['net_revenue'], order['profit'], order['status'],
            ),
        )

        order_id = row['id']

        for item in order.get('items', []):
            execute_query(
                """
                INSERT INTO order_items (order_id, item_name, quantity, unit_price, line_total)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (order_id, item['name'], item['quantity'], item['unit_price'],
                 item['quantity'] * item['unit_price']),
                fetch=False,
            )

        return 'created'

    # ---------- Main ----------

    def run(self, integration, count=15):
        start = datetime.utcnow()
        self.start_log()

        try:
            orders = integration.fetch_orders(count=count)
            self.stats['fetched'] = len(orders)

            for order in orders:
                try:
                    result = self.upsert_order(order)
                    if result == 'created':
                        self.stats['created'] += 1
                    else:
                        self.stats['updated'] += 1
                except Exception as e:
                    self.stats['failed'] += 1
                    print(f"Order failed: {e}")

            duration = (datetime.utcnow() - start).total_seconds()
            self.finish_log('success', duration=duration)

            execute_query(
                """
                UPDATE integrations
                SET last_sync_at = NOW(), last_successful_sync = NOW(),
                    last_error = NULL, updated_at = NOW()
                WHERE id = %s
                """,
                (self.integration_id,),
                fetch=False,
            )

            # Notify on new orders
            if self.stats['created'] > 0:
                try:
                    notif.notify_sync_success(self.kitchen_id, self.platform, self.stats['created'])
                except Exception as _e:
                    print(f'[sync] notif failed: {_e}')

            return {'status': 'success', **self.stats, 'duration': round(duration, 2)}

        except Exception as e:
            duration = (datetime.utcnow() - start).total_seconds()
            self.finish_log('failed', error_message=str(e), duration=duration)
            execute_query(
                """
                UPDATE integrations
                SET last_sync_at = NOW(), last_error = %s, updated_at = NOW()
                WHERE id = %s
                """,
                (str(e)[:500], self.integration_id),
                fetch=False,
            )
            try:
                notif.notify_sync_failed(self.kitchen_id, self.platform, str(e))
            except Exception as _e:
                print(f'[sync] notif failed: {_e}')

            # Send email alert to kitchen owner
            try:
                from db.connection import execute_one
                owner = execute_one('''
                    SELECT u.id, u.email, u.full_name
                    FROM kitchens k
                    JOIN users u ON u.id = k.user_id
                    WHERE k.id = %s
                ''', (self.kitchen_id,))
                if owner:
                    email_service.send_sync_alert(
                        owner['id'], owner['email'], self.platform,
                        str(e), kitchen_name=f"kitchen #{self.kitchen_id}"
                    )
            except Exception as _e:
                print(f'[sync] email failed: {_e}')

            return {'status': 'failed', 'error': str(e), **self.stats}