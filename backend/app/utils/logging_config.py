"""
KitchenIQ — Structured Logging
JSON logs for production, human-readable for dev.
"""
import os
import json
import logging
import sys
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key in ("user_id", "kitchen_id", "path", "method", "status", "duration_ms", "ip"):
            if hasattr(record, key):
                log_data[key] = getattr(record, key)

        return json.dumps(log_data)


class DevFormatter(logging.Formatter):
    """Human-readable format for development."""

    def format(self, record):
        colors = {
            "DEBUG": "\033[36m",
            "INFO": "\033[32m",
            "WARNING": "\033[33m",
            "ERROR": "\033[31m",
            "CRITICAL": "\033[35m",
        }
        reset = "\033[0m"
        color = colors.get(record.levelname, "")

        time_str = datetime.now().strftime("%H:%M:%S")
        return f"{color}[{time_str}] {record.levelname:8s}{reset} {record.name}: {record.getMessage()}"


def setup_logging(app=None):
    """Configure logging for the whole app."""
    env = os.getenv("FLASK_ENV", "development")
    is_production = env == "production" or os.getenv("RENDER")

    # Root logger
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if is_production:
        handler.setFormatter(JSONFormatter())
        root.setLevel(logging.INFO)
    else:
        handler.setFormatter(DevFormatter())
        root.setLevel(logging.INFO)

    root.addHandler(handler)

    # Silence noisy loggers
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    if app:
        app.logger.handlers.clear()
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)

    return root


def request_logger(app):
    """Add request/response logging middleware."""

    @app.before_request
    def _log_request_start():
        from flask import request, g
        import time
        g._request_start = time.time()

    @app.after_request
    def _log_request_end(response):
        from flask import request, g
        import time
        import logging

        if hasattr(g, "_request_start"):
            duration_ms = round((time.time() - g._request_start) * 1000, 2)

            # Skip health checks (noisy)
            if request.path in ("/api/health", "/api/ready"):
                return response

            logger = logging.getLogger("kitcheniq.request")
            logger.info(
                f"{request.method} {request.path} → {response.status_code} ({duration_ms}ms)",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "ip": request.remote_addr,
                    "user_id": getattr(request, "user_id", None),
                },
            )

        return response
