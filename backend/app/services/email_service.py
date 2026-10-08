"""
KitchenIQ — Email Service (SendGrid)
Transactional emails with mock mode.
"""

import os
from datetime import datetime

from dotenv import load_dotenv

from db.connection import execute_query, execute_one


load_dotenv()


def _is_mock():
    """Return True when email mock mode is enabled."""
    return os.getenv("EMAIL_MOCK_MODE", "false").lower() == "true"


def _get_client():
    """Create and return the SendGrid client."""
    if _is_mock():
        return None

    try:
        from sendgrid import SendGridAPIClient

        api_key = os.getenv("SENDGRID_API_KEY")

        if not api_key or api_key == "SG.mock_key":
            return None

        return SendGridAPIClient(api_key)

    except Exception as e:
        print(f"[email] client init failed: {e}")
        return None


# ============================================================
# CORE SEND
# ============================================================

def send_email(
    to_email,
    subject,
    html_content,
    template="generic",
    user_id=None,
    metadata=None,
):
    """
    Send an email and log the result to email_logs.

    In mock mode, prints the email information to the console
    instead of sending through SendGrid.
    """

    # Check user preferences
    if user_id:
        pref_map = {
            "welcome": "welcome_email",
            "payment_receipt": "payment_receipts",
            "weekly_digest": "weekly_digest",
            "sync_alert": "sync_alerts",
        }

        pref_field = pref_map.get(template)

        if pref_field:
            pref = execute_one(
                f"SELECT {pref_field} FROM email_preferences WHERE user_id = %s",
                (user_id,),
            )

            if pref and pref[pref_field] is False:
                _log_email(
                    user_id,
                    to_email,
                    subject,
                    template,
                    "skipped",
                    None,
                    "User opted out",
                    metadata,
                )

                return {
                    "status": "skipped",
                    "reason": "opted_out",
                }

    # --------------------------------------------------------
    # Mock mode
    # --------------------------------------------------------

    if _is_mock():
        print(f"\n{'=' * 60}")
        print("📧 [MOCK EMAIL]")
        print(f"   To:      {to_email}")
        print(f"   Subject: {subject}")
        print(f"   Template: {template}")
        print(f"   Time:    {datetime.now().isoformat()}")
        print(f"{'=' * 60}\n")

        _log_email(
            user_id,
            to_email,
            subject,
            template,
            "mock_sent",
            "mock_id_" + str(int(datetime.now().timestamp())),
            None,
            metadata,
        )

        return {
            "status": "mock_sent",
            "to": to_email,
        }

    # --------------------------------------------------------
    # Real SendGrid
    # --------------------------------------------------------

    client = _get_client()

    if not client:
        _log_email(
            user_id,
            to_email,
            subject,
            template,
            "failed",
            None,
            "No API key",
            metadata,
        )

        return {
            "status": "failed",
            "reason": "no_api_key",
        }

    try:
        from sendgrid.helpers.mail import Mail, Email, To, Content

        from_email = Email(
            os.getenv(
                "SENDGRID_FROM_EMAIL",
                "noreply@kitcheniq.in",
            ),
            os.getenv(
                "SENDGRID_FROM_NAME",
                "KitchenIQ",
            ),
        )

        to = To(to_email)

        content = Content(
            "text/html",
            html_content,
        )

        mail = Mail(
            from_email,
            to,
            subject,
            content,
        )

        response = client.send(mail)

        provider_id = response.headers.get("X-Message-Id")

        _log_email(
            user_id,
            to_email,
            subject,
            template,
            "sent",
            provider_id,
            None,
            metadata,
        )

        return {
            "status": "sent",
            "provider_id": provider_id,
        }

    except Exception as e:
        error = str(e)[:300]

        _log_email(
            user_id,
            to_email,
            subject,
            template,
            "failed",
            None,
            error,
            metadata,
        )

        return {
            "status": "failed",
            "error": error,
        }


def _log_email(
    user_id,
    to_email,
    subject,
    template,
    status,
    provider_id,
    error,
    metadata=None,
):
    """Write an email delivery record to email_logs."""

    try:
        execute_query(
            """
            INSERT INTO email_logs
                (
                    user_id,
                    to_email,
                    subject,
                    template,
                    status,
                    provider_id,
                    error_message,
                    metadata
                )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                to_email,
                subject,
                template,
                status,
                provider_id,
                error,
                metadata,
            ),
            fetch=False,
        )

    except Exception as e:
        print(f"[email] log failed: {e}")


# ============================================================
# EMAIL TEMPLATES
# ============================================================

def _base_template(title, body_html):
    """Wrap content in a branded KitchenIQ email template."""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">

        <style>
            body {{
                font-family:
                    -apple-system,
                    BlinkMacSystemFont,
                    'Segoe UI',
                    Roboto,
                    sans-serif;
                margin: 0;
                padding: 0;
                background: #f1f5f9;
            }}

            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: white;
            }}

            .header {{
                background:
                    linear-gradient(
                        135deg,
                        #2563eb 0%,
                        #4f46e5 100%
                    );
                color: white;
                padding: 32px;
                text-align: center;
            }}

            .logo {{
                font-size: 24px;
                font-weight: 700;
            }}

            .body {{
                padding: 32px;
                color: #0f172a;
                line-height: 1.6;
            }}

            .btn {{
                display: inline-block;
                background: #2563eb;
                color: white !important;
                padding: 12px 28px;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                margin: 20px 0;
            }}

            .footer {{
                padding: 24px 32px;
                text-align: center;
                font-size: 12px;
                color: #64748b;
                border-top: 1px solid #e2e8f0;
                background: #f8fafc;
            }}

            .kpi {{
                background: #f1f5f9;
                padding: 16px;
                border-radius: 8px;
                margin: 12px 0;
            }}

            .kpi-value {{
                font-size: 24px;
                font-weight: 700;
                color: #2563eb;
            }}

            .kpi-label {{
                font-size: 12px;
                color: #64748b;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
        </style>
    </head>

    <body>
        <div class="container">

            <div class="header">
                <div class="logo">🍽️ KitchenIQ</div>

                <div
                    style="
                        opacity: 0.9;
                        margin-top: 8px;
                        font-size: 14px;
                    "
                >
                    {title}
                </div>
            </div>

            <div class="body">
                {body_html}
            </div>

            <div class="footer">
                <p>
                    You're receiving this email because you
                    have a KitchenIQ account.
                </p>

                <p>
                    © 2026 KitchenIQ ·
                    <a href="#" style="color: #64748b;">
                        Unsubscribe
                    </a>
                </p>
            </div>

        </div>
    </body>
    </html>
    """


# ============================================================
# EMAIL FUNCTIONS
# ============================================================

def send_welcome_email(user_id, email, full_name):
    """Send welcome email on signup."""

    name = full_name or email.split("@")[0]

    html = _base_template(
        "Welcome to KitchenIQ!",
        f"""
        <h1 style="font-size: 22px; margin-top: 0;">
            Hi {name} 👋
        </h1>

        <p>
            Welcome to KitchenIQ — your new analytics
            platform for cloud kitchens.
        </p>

        <p>
            <strong>Get started in 3 easy steps:</strong>
        </p>

        <ol style="padding-left: 20px;">
            <li style="padding: 6px 0;">
                Upload your orders (CSV or connect a platform)
            </li>

            <li style="padding: 6px 0;">
                See your dashboard with KPIs and charts
            </li>

            <li style="padding: 6px 0;">
                Get AI-powered insights to grow profit
            </li>
        </ol>

        <div style="text-align: center;">
            <a
                href="http://localhost:5500/pages/dashboard.html"
                class="btn"
            >
                Go to Dashboard →
            </a>
        </div>

        <p style="margin-top: 32px;">
            Need help? Just reply to this email.
        </p>

        <p>
            — Team KitchenIQ
        </p>
        """,
    )

    return send_email(
        email,
        "Welcome to KitchenIQ 🎉",
        html,
        template="welcome",
        user_id=user_id,
    )


def send_payment_receipt(
    user_id,
    email,
    full_name,
    plan,
    amount,
    expires_at,
    payment_id,
):
    """Send payment receipt after successful subscription."""

    name = full_name or email.split("@")[0]
    plan_name = plan.capitalize()

    html = _base_template(
        "Payment Receipt",
        f"""
        <h1 style="font-size: 22px; margin-top: 0;">
            Payment successful 🎉
        </h1>

        <p>
            Hi {name}, your
            <strong>{plan_name} Plan</strong>
            subscription is now active.
        </p>

        <div class="kpi">
            <div class="kpi-label">
                Plan
            </div>

            <div
                class="kpi-value"
                style="color: #10b981;"
            >
                {plan_name}
            </div>
        </div>

        <div class="kpi">
            <div class="kpi-label">
                Amount Paid
            </div>

            <div class="kpi-value">
                ₹{amount:,.2f}
            </div>
        </div>

        <div class="kpi">
            <div class="kpi-label">
                Valid Until
            </div>

            <div
                class="kpi-value"
                style="
                    color: #0f172a;
                    font-size: 18px;
                "
            >
                {expires_at}
            </div>
        </div>

        <p
            style="
                font-size: 12px;
                color: #64748b;
                margin-top: 20px;
            "
        >
            Payment ID:
            <code>{payment_id}</code>
        </p>

        <div style="text-align: center;">
            <a
                href="http://localhost:5500/pages/plans.html"
                class="btn"
            >
                View Subscription →
            </a>
        </div>
        """,
    )

    return send_email(
        email,
        f"Payment Receipt — {plan_name} Plan",
        html,
        template="payment_receipt",
        user_id=user_id,
    )


def send_weekly_digest(
    user_id,
    email,
    kitchen_name,
    stats,
):
    """Send weekly sales digest."""

    html = _base_template(
        f"Weekly Digest — {kitchen_name}",
        f"""
        <h1 style="font-size: 22px; margin-top: 0;">
            Your weekly summary 📊
        </h1>

        <p>
            Here's how
            <strong>{kitchen_name}</strong>
            performed this week:
        </p>

        <div class="kpi">
            <div class="kpi-label">
                Total Revenue
            </div>

            <div class="kpi-value">
                ₹{stats.get("revenue", 0):,.0f}
            </div>
        </div>

        <div class="kpi">
            <div class="kpi-label">
                Total Orders
            </div>

            <div class="kpi-value">
                {stats.get("orders", 0)}
            </div>
        </div>

        <div class="kpi">
            <div class="kpi-label">
                Net Profit
            </div>

            <div
                class="kpi-value"
                style="color: #10b981;"
            >
                ₹{stats.get("profit", 0):,.0f}
            </div>
        </div>

        <div class="kpi">
            <div class="kpi-label">
                Avg. Order Value
            </div>

            <div class="kpi-value">
                ₹{stats.get("aov", 0):,.0f}
            </div>
        </div>

        <div style="text-align: center;">
            <a
                href="http://localhost:5500/pages/dashboard.html"
                class="btn"
            >
                View Full Dashboard →
            </a>
        </div>
        """,
    )

    return send_email(
        email,
        f"Weekly Digest — {kitchen_name}",
        html,
        template="weekly_digest",
        user_id=user_id,
    )


def send_sync_alert(
    user_id,
    email,
    platform,
    error,
    kitchen_name="your kitchen",
):
    """Send alert when integration sync fails."""

    html = _base_template(
        f"Sync Failed — {platform.capitalize()}",
        f"""
        <h1 style="font-size: 22px; margin-top: 0;">
            ⚠️ Sync failed
        </h1>

        <p>
            We couldn't sync orders from
            <strong>{platform.capitalize()}</strong>
            for {kitchen_name}.
        </p>

        <div
            style="
                background: #fef2f2;
                border: 1px solid #fecaca;
                padding: 16px;
                border-radius: 8px;
                margin: 20px 0;
            "
        >
            <div
                style="
                    font-size: 12px;
                    color: #b91c1c;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    margin-bottom: 6px;
                "
            >
                Error
            </div>

            <code style="color: #7f1d1d;">
                {str(error)[:200]}
            </code>
        </div>

        <p>
            <strong>What to do:</strong>
        </p>

        <ol style="padding-left: 20px;">
            <li style="padding: 4px 0;">
                Check the integration status in KitchenIQ
            </li>

            <li style="padding: 4px 0;">
                Try reconnecting the platform
            </li>

            <li style="padding: 4px 0;">
                If issue persists, contact support
            </li>
        </ol>

        <div style="text-align: center;">
            <a
                href="http://localhost:5500/pages/integrations.html"
                class="btn"
            >
                Check Integrations →
            </a>
        </div>
        """,
    )

    return send_email(
        email,
        f"⚠️ Sync failed for {platform.capitalize()}",
        html,
        template="sync_alert",
        user_id=user_id,
    )
