# ============================================================
# KitchenIQ Backend — Dockerfile
# Multi-stage build for smaller production image
# ============================================================

# ---------- Stage 1: Builder ----------
FROM python:3.11-slim AS builder

WORKDIR /build

# Build dependencies for psycopg2, cryptography, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ---------- Stage 2: Runtime ----------
FROM python:3.11-slim

# Runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m -u 1000 appuser

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy backend code
COPY --chown=appuser:appuser backend/ /app/

# Copy migration scripts
COPY --chown=appuser:appuser scripts/ /app/scripts/

# Ensure uploads dir exists
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app/uploads

USER appuser

# Env
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000 \
    FLASK_ENV=production

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:5000/api/health || exit 1

# Start server
# Copy entrypoint
COPY --chown=appuser:appuser docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
