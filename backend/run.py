"""
KitchenIQ — Flask Application
"""
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from dotenv import load_dotenv
import os
import logging

load_dotenv()

# Structured logging
from app.utils.logging_config import setup_logging, request_logger


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

    # Logging
    setup_logging(app)
    request_logger(app)

    # CORS
    CORS(app, resources={r"/*": {"origins": "*"}})

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            resp = make_response()
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Kitchen-Id"
            resp.headers["Access-Control-Max-Age"] = "3600"
            return resp

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Kitchen-Id"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    # ========================================================
    # Blueprints
    # ========================================================
    from app.routes.auth import auth_bp
    from app.routes.upload import upload_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.analytics import analytics_bp
    from app.routes.customers import customers_bp
    from app.routes.dishes import dishes_bp
    from app.routes.finance import finance_bp
    from app.routes.foodcost import foodcost_bp
    from app.routes.integrations import integrations_bp
    from app.routes.insights import insights_bp
    from app.routes.notifications import notifications_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp
    from app.routes.team import team_bp
    from app.routes.search import search_bp
    from app.routes.worker import worker_bp
    from app.routes.kitchens import kitchens_bp
    from app.routes.audit import audit_bp
    from app.routes.live import live_bp
    from app.routes.plans import plans_bp
    from app.routes.public import public_bp
    from app.routes.oauth import oauth_bp
    from app.routes.payments import payments_bp
    from app.routes.emails import emails_bp
    from app.routes.monitoring import monitoring_bp
    from app.routes.forecast import forecast_bp

    app.register_blueprint(auth_bp,          url_prefix="/api/auth")
    app.register_blueprint(upload_bp,        url_prefix="/api/upload")
    app.register_blueprint(dashboard_bp,     url_prefix="/api/dashboard")
    app.register_blueprint(analytics_bp,     url_prefix="/api/analytics")
    app.register_blueprint(customers_bp,     url_prefix="/api/customers")
    app.register_blueprint(dishes_bp,        url_prefix="/api/dishes")
    app.register_blueprint(finance_bp,       url_prefix="/api/finance")
    app.register_blueprint(foodcost_bp,      url_prefix="/api/foodcost")
    app.register_blueprint(integrations_bp,  url_prefix="/api/integrations")
    app.register_blueprint(insights_bp,      url_prefix="/api/insights")
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")
    app.register_blueprint(reports_bp,       url_prefix="/api/reports")
    app.register_blueprint(settings_bp,      url_prefix="/api/settings")
    app.register_blueprint(team_bp,          url_prefix="/api/team")
    app.register_blueprint(search_bp,        url_prefix="/api/search")
    app.register_blueprint(worker_bp,        url_prefix="/api/worker")
    app.register_blueprint(kitchens_bp,      url_prefix="/api/kitchens")
    app.register_blueprint(audit_bp,         url_prefix="/api/audit")
    app.register_blueprint(live_bp,          url_prefix="/api/live")
    app.register_blueprint(plans_bp,         url_prefix="/api/plans")
    app.register_blueprint(public_bp,        url_prefix="/api/public")
    app.register_blueprint(oauth_bp,         url_prefix="/api/oauth")
    app.register_blueprint(payments_bp,      url_prefix="/api/payments")
    app.register_blueprint(emails_bp,        url_prefix="/api/emails")
    app.register_blueprint(monitoring_bp,    url_prefix="/api/monitoring")
    app.register_blueprint(forecast_bp,      url_prefix="/api/forecast")

    # ========================================================
    # Direct routes
    # ========================================================
    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "KitchenIQ API", "version": "0.3.0"})

    @app.route("/")
    def root():
        return jsonify({"service": "KitchenIQ", "message": "Visit /api/health"})

    # ========================================================
    # Errors
    # ========================================================
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        tb = traceback.format_exc()
        print("\n========== ERROR ==========")
        print(tb)
        print("===========================\n")
        return jsonify({"error": "Server error", "detail": str(e)}), 500

    # Worker (only in main process)
    from app.workers.sync_worker import start_scheduler
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        try:
            start_scheduler(app, interval_minutes=5)
        except Exception as _e:
            app.logger.error(f"Failed to start scheduler: {_e}")

# Sentry (optional — only if DSN is set)
    _init_sentry(app)

    return app


def _init_sentry(app):
    """Initialize Sentry for error tracking (no-op if DSN empty)."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            environment=os.getenv("FLASK_ENV", "production"),
            release=os.getenv("APP_VERSION", "0.3.0"),
        )
        app.logger.info("✅ Sentry initialized")
    except Exception as e:
        app.logger.warning(f"Sentry init failed: {e}")



app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5050")), debug=False, use_reloader=False)
