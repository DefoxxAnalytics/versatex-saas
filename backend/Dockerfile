# ---- Builder stage: compile wheels with full toolchain ----
FROM python:3.11-slim@sha256:6d85378d88a19cd4d76079817532d62232be95757cb45945a99fec8e8084b9c2 AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    musl-dev \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt


# ---- Runtime stage: slim image with only runtime libs ----
FROM python:3.11-slim@sha256:6d85378d88a19cd4d76079817532d62232be95757cb45945a99fec8e8084b9c2

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Runtime-only system deps:
#   libpq5    - PostgreSQL client lib (replaces libpq-dev from builder)
#   libmagic1 - file-type detection used by python-magic
#   curl      - required by backend healthcheck in docker-compose.yml
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy installed Python packages from the builder stage
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy project source
COPY . .

# Make entrypoint executable. collectstatic now runs at container start with
# the real runtime env (see entrypoint.sh) instead of at build time, where
# SECRET_KEY was missing and `|| true` masked any failure.
RUN chmod +x /app/entrypoint.sh

# Create media and logs directories
RUN mkdir -p /app/media /app/logs

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run gunicorn through entrypoint (collectstatic + exec)
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
