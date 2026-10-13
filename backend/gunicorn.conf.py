"""KitchenIQ — Gunicorn Production Config"""
import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048
workers = int(os.getenv('WEB_CONCURRENCY', '2'))
worker_class = "gthread"
threads = int(os.getenv('GUNICORN_THREADS', '4'))
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 120
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = os.getenv('LOG_LEVEL', 'info')
proc_name = "kitcheniq-api"
preload_app = False