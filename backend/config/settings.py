"""
Django settings for Analytics Dashboard
"""

import os
import sys
import logging
import secrets
from pathlib import Path
from datetime import timedelta
from decouple import config
from django.core.exceptions import ImproperlyConfigured

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security - CRITICAL: No default SECRET_KEY
def get_secret_key():
    """Get SECRET_KEY from environment, raise error if not set in production."""
    key = config('SECRET_KEY', default='')
    if not key:
        # Allow insecure key only in development with explicit DEBUG=True
        if config('DEBUG', default=False, cast=bool):
            logging.warning(
                "⚠️  Using insecure SECRET_KEY for development. "
                "Set SECRET_KEY environment variable for production!"
            )
            return 'django-insecure-dev-only-key-do-not-use-in-production'
        raise ImproperlyConfigured(
            "SECRET_KEY environment variable is required in production. "
            "Generate one with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
        )
    return key

SECRET_KEY = get_secret_key()

# CRITICAL: DEBUG defaults to False for security
DEBUG = config('DEBUG', default=False, cast=bool)

# Warn if DEBUG is True in a production-like environment
if DEBUG and 'runserver' not in sys.argv:
    logging.warning("⚠️  DEBUG=True detected outside of development server!")

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Finding A2: IPs from which X-Real-IP / X-Forwarded-For headers are honored
# by apps.authentication.utils.get_client_ip. Without this allowlist, any
# client could spoof X-Real-IP to defeat the per-IP-scoped lockout key and
# pollute audit logs. Empty default = forwarded headers ignored entirely;
# only direct REMOTE_ADDR is used. Production behind nginx: set to the
# upstream IP (typically 127.0.0.1 if same-host, or the docker bridge IP).
TRUSTED_PROXIES = config('TRUSTED_PROXIES', default='').split(',') if config('TRUSTED_PROXIES', default='') else []

# First-deploy footgun: without TRUSTED_PROXIES set, get_client_ip() ignores
# X-Forwarded-For from the reverse proxy, so login attempts log the proxy IP
# instead of the real client and per-IP rate limiting collapses to a single
# bucket. Use the module logger so the message routes through Django's logging
# config rather than the root handler.
if not DEBUG and not TRUSTED_PROXIES:
    logging.getLogger(__name__).warning(
        "TRUSTED_PROXIES is empty in production. Real client IPs may not "
        "be detected from X-Forwarded-For. Set TRUSTED_PROXIES env var to "
        "the comma-separated CIDR list of your reverse proxy (e.g., "
        "Railway/Cloudflare ranges)."
    )

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',

    # Local apps
    'apps.authentication',
    'apps.procurement',
    'apps.analytics',
    'apps.reports',
    'apps.health',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.DeprecationMiddleware',  # Adds deprecation headers to legacy endpoints
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='analytics_db'),
        'USER': config('DB_USER', default='analytics_user'),
        'PASSWORD': config('DB_PASSWORD', default='analytics_pass'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        # Persistent connections cut the per-request handshake; health checks
        # keep zombie connections from being served after Postgres restarts.
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'connect_timeout': 10,
            # 'prefer' default keeps dev (no SSL setup) working — Postgres
            # falls back to non-SSL when the server doesn't support it.
            # Production-managed Postgres (Railway, RDS) sets DB_SSLMODE=require
            # to enforce TLS without code changes. 'verify-full' adds CA + host
            # validation when a CA bundle is plumbed through.
            'sslmode': config('DB_SSLMODE', default='prefer'),
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Password Hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'  # EST/EDT
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Storage backends (Django 5 STORAGES API). Always defined — Django rejects
# coexistence with the legacy STATICFILES_STORAGE setting ("mutually exclusive").
# media ('default'): Cloudflare R2 when USE_R2_MEDIA=True, else local filesystem.
# static ('staticfiles'): whitenoise CompressedManifest in prod (needs
#   collectstatic); settings_test.py overrides to plain StaticFilesStorage for
#   pytest, where collectstatic is skipped.
if config('USE_R2_MEDIA', default=False, cast=bool):
    _default_storage = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': config('R2_MEDIA_BUCKET', default='versatex-media'),
            'endpoint_url': config('R2_ENDPOINT', default=''),
            'access_key': config('R2_ACCESS_KEY_ID', default=''),
            'secret_key': config('R2_SECRET_ACCESS_KEY', default=''),
            'region_name': 'auto',       # R2 convention
            'default_acl': 'private',
            'querystring_auth': True,    # presigned URLs for reads
            'querystring_expire': 3600,
        },
    }
else:
    _default_storage = {'BACKEND': 'django.core.files.storage.FileSystemStorage'}

STORAGES = {
    'default': _default_storage,
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# File upload limits — keep in lockstep with frontend/nginx/nginx.conf
# `client_max_body_size`. Misalignment lets nginx accept payloads that
# Django then rejects with a confusing "request body exceeded" 400.
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'apps.authentication.backends.CookieJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        # Scoped throttle rates for specific operations
        'uploads': '10/hour',       # File upload rate limiting
        'exports': '30/hour',       # Export rate limiting
        'bulk_delete': '10/hour',   # Bulk delete rate limiting
        'login': '5/minute',        # Login rate limiting (backup to django-ratelimit)
        'read_api': '500/hour',     # Read operations rate limiting
        'ai_insights': '30/hour',   # AI insights rate limiting (expensive computation)
        'predictions': '60/hour',   # Predictions rate limiting
        'contract_analytics': '100/hour',  # Contract analytics rate limiting
        'compliance': '100/hour',  # Compliance rate limiting
        'report_generate': '20/hour',  # Report generation rate limiting (expensive)
        'report_download': '60/hour',  # Report download rate limiting
        'p2p_analytics': '200/hour',   # P2P analytics read operations
        'p2p_write': '30/hour',        # P2P write operations (exception resolution)
    },
    'EXCEPTION_HANDLER': 'config.exception_handler.custom_exception_handler',
}

# JWT Settings - Reduced token lifetime for security
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),  # Reduced from 1 hour
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),     # Reduced from 7 days
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'UPDATE_LAST_LOGIN': True,
    # Cookie-based JWT settings for XSS protection
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_REFRESH': 'refresh_token',
    'AUTH_COOKIE_DOMAIN': None,  # Use request domain
    'AUTH_COOKIE_SECURE': not DEBUG,  # HTTPS only in production
    'AUTH_COOKIE_HTTP_ONLY': True,  # Prevent JavaScript access
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_SAMESITE': 'Lax',
}

# CORS Settings - Strict configuration
# Parse allowed origins from environment
_cors_origins = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:5173'
).split(',')

# Helper to check if origin is for local development
def _is_local_origin(origin):
    """Check if origin is localhost or 127.0.0.1 (local development)"""
    return 'localhost' in origin or '127.0.0.1' in origin

# In production, only allow HTTPS origins (except for local development)
if not DEBUG:
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in _cors_origins
        if origin.strip().startswith('https://') or _is_local_origin(origin)
    ]
    # Warn if non-HTTPS origins are configured in production
    _insecure_origins = [o for o in _cors_origins if not o.strip().startswith('https://') and not _is_local_origin(o)]
    if _insecure_origins:
        logging.warning(f"⚠️  Insecure CORS origins configured (should use HTTPS): {_insecure_origins}")
else:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins]

# Only allow credentials with explicit origin whitelist (not wildcards)
# IMPORTANT: CORS_ALLOW_CREDENTIALS should only be True if origins are explicitly listed
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # Never allow all origins with credentials

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Limit CORS methods to only what's needed
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# CSRF Settings
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:3000,http://localhost:5173'
).split(',')
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Session Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 1800  # 30 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Email Configuration
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@versatexanalytics.com')

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
# Finding A6: explicit task-result expiration (Celery's default is 24h with
# the Redis backend, but making it explicit lets ops tune without surprise
# and documents the policy. 1h = enough for status polling on long uploads,
# short enough that Redis OOM risk stays bounded.)
CELERY_RESULT_EXPIRES = config('CELERY_RESULT_EXPIRES', default=3600, cast=int)

# Django Cache Configuration (Redis)
# Uses Django's native Redis backend (Django 4.0+)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
        'KEY_PREFIX': 'versatex',
        'TIMEOUT': 3600,  # 1 hour default TTL
    }
}

# AI Insights Cache Settings
AI_INSIGHTS_CACHE_TTL = config('AI_INSIGHTS_CACHE_TTL', default=3600, cast=int)  # 1 hour

# API Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'Versatex Analytics API',
    'DESCRIPTION': '''
REST API for Versatex Analytics - Enterprise Procurement Analytics Platform.

## Overview
This API provides endpoints for:
- **Authentication**: User registration, login, JWT tokens
- **Procurement**: Suppliers, categories, transactions, CSV uploads
- **Analytics**: Spend analysis, Pareto, stratification, seasonality, YoY
- **Reports**: Report generation, scheduling, downloads (PDF/Excel/CSV)
- **P2P Analytics**: Procure-to-Pay cycle analysis, 3-way matching, invoice aging

## Authentication
All endpoints require JWT authentication. Include the access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## Multi-Tenancy
Data is scoped by organization. Superusers can specify `organization_id` query parameter.
    ''',
    'VERSION': '2.5.0',
    'TAGS': [
        {'name': 'Authentication', 'description': 'User authentication and authorization'},
        {'name': 'Procurement', 'description': 'Suppliers, categories, and transactions'},
        {'name': 'Analytics', 'description': 'Spend analytics and insights'},
        {'name': 'Reports', 'description': 'Report generation and scheduling'},
        {'name': 'P2P Analytics - Cycle Time', 'description': 'P2P process cycle time analysis'},
        {'name': 'P2P Analytics - 3-Way Matching', 'description': 'Invoice matching and exception management'},
        {'name': 'P2P Analytics - Invoice Aging', 'description': 'Accounts payable aging analysis'},
        {'name': 'P2P Analytics - Requisitions', 'description': 'Purchase requisition analytics'},
        {'name': 'P2P Analytics - Purchase Orders', 'description': 'Purchase order analytics and compliance'},
        {'name': 'P2P Analytics - Supplier Payments', 'description': 'Supplier payment performance (Admin only)'},
    ],
    'CONTACT': {'name': 'Defoxx Analytics', 'url': 'https://github.com/DefoxxAnalytics'},
    'LICENSE': {'name': 'Proprietary'},
}

# Security Settings - Always applied (not just in production)
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Production Security Settings
if not DEBUG:
    # HTTPS enforcement
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Trust X-Forwarded-Proto from the reverse proxy. Request path in prod is
    # browser(https) -> Cloudflare edge(https) -> cloudflared tunnel(https) ->
    # nginx(http) -> Django. Without this header trust, SECURE_SSL_REDIRECT
    # sees http from nginx and issues a 301 -> https that Django already
    # received -> infinite loop. Paired with the X-Forwarded-Proto pass-through
    # map in frontend/nginx/nginx.conf so Cloudflare's header survives the
    # plaintext tunnel->nginx hop.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # HSTS - enforce HTTPS for 1 year (Finding #15).
    # Paired with the Strict-Transport-Security header in frontend/nginx/nginx.conf
    # so the header is emitted whether the request hits Django directly (no
    # nginx in front) or via the canonical nginx -> backend path. Gated on
    # `not DEBUG` to avoid breaking dev with self-signed certs.
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    # includeSubDomains is irreversible for max-age's duration and pins every
    # *.versatexanalytics.com subdomain to HTTPS. Env-gated so staging/sandbox
    # subdomains can opt in deliberately after 1 week of prod validation.
    # Default False -> header emitted without the includeSubDomains / preload
    # directives -> safe rollback path.
    # To enable preload (irreversible for max-age): set HSTS_PRELOAD=True after
    # ≥1 week of prod validation, redeploy, then submit at https://hstspreload.org/.
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config('HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
    SECURE_HSTS_PRELOAD = config('HSTS_PRELOAD', default=False, cast=bool)

    # Referrer policy
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

    # Prevent clickjacking
    X_FRAME_OPTIONS = 'DENY'

# Admin Site Configuration
# Dynamic admin URL: if not set, generate random path on each startup for security
_env_admin_url = config('ADMIN_URL', default='')
if _env_admin_url:
    ADMIN_URL = _env_admin_url if _env_admin_url.endswith('/') else f'{_env_admin_url}/'
else:
    # Generate dynamic admin URL for security (prevents enumeration)
    ADMIN_URL = f'manage-{secrets.token_hex(8)}/'
    logging.info(f"Dynamic admin URL generated: /{ADMIN_URL}")
LOGOUT_REDIRECT_URL = f'/{ADMIN_URL}login/'

# Frontend URL for "View Site" link in admin
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')

# Field Encryption (optional - for django-encrypted-model-fields)
# Generate key with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY = config('FIELD_ENCRYPTION_KEY', default='')

# LLM provider keys. Read via getattr(settings, 'ANTHROPIC_API_KEY', None) in
# apps/analytics/{views.py, rag_service.py, semantic_cache.py, document_ingestion.py}.
# Before this declaration they silently resolved to None and AI enhancement
# degraded to deterministic-only output without any log signal.
# Empty default is intentional — deployment may run without external AI.
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')

# AI streaming chat payload bounds (Finding B10).
# Defaults are conservative; ops can override via env. Combined with the
# per-call AIInsightsThrottle (Finding #7), these prevent single-call
# cost-blast attacks (e.g., one 10MB chat history hitting the LLM with
# millions of input tokens).
AI_CHAT_MAX_MESSAGES = config('AI_CHAT_MAX_MESSAGES', default=50, cast=int)
AI_CHAT_MAX_MESSAGE_CONTENT_CHARS = config(
    'AI_CHAT_MAX_MESSAGE_CONTENT_CHARS', default=8000, cast=int
)
AI_CHAT_MAX_PAYLOAD_BYTES = config(
    'AI_CHAT_MAX_PAYLOAD_BYTES', default=200_000, cast=int
)

# AI streaming chat model allowlist (Finding #8 permanent fix).
# Phase 0 hardcoded the model; Phase 4 task 4.2 replaces that with a
# settings-driven allowlist + default. Add new model strings here when
# upgrading; do NOT accept unknown values from the client (Opus is ~5x
# Sonnet pricing — a single mis-pointed model burns the daily budget).
# Note: AI_CHAT_DEFAULT_MODEL MUST be present in AI_CHAT_ALLOWED_MODELS
# for the validation to be coherent (the default is what we fall back to
# when no client-supplied value is present, and it is then re-checked
# against the allowlist).
AI_CHAT_ALLOWED_MODELS = config(
    'AI_CHAT_ALLOWED_MODELS',
    default='claude-sonnet-4-20250514',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)
AI_CHAT_DEFAULT_MODEL = config(
    'AI_CHAT_DEFAULT_MODEL',
    default='claude-sonnet-4-20250514',
)

# Daily LLM cost-digest webhook (ntfy.sh / Slack / Teams compatible).
# When empty, send_llm_cost_digest task logs the daily rollup but skips the
# outbound POST. Set to an ntfy.sh topic URL for zero-friction alerting.
COST_ALERT_WEBHOOK_URL = config('COST_ALERT_WEBHOOK_URL', default='')

# Logging configuration for security events
# Build handlers dict - only include file handler in production
_logging_handlers = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
    },
}

# Only add file handlers in production (non-DEBUG mode)
if not DEBUG:
    # Create logs directory if it doesn't exist
    (BASE_DIR / 'logs').mkdir(exist_ok=True)
    _logging_handlers['security_file'] = {
        'class': 'logging.FileHandler',
        'filename': BASE_DIR / 'logs' / 'security.log',
        'formatter': 'verbose',
        # Strip aiApiKey/password/Authorization/token values from records
        # before they hit the persisted security log volume.
        'filters': ['redact_sensitive'],
    }

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'redact_sensitive': {
            '()': 'config.logging_filters.RedactSensitiveFilter',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': _logging_handlers,
    'loggers': {
        'django.security': {
            'handlers': ['console', 'security_file'] if not DEBUG else ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'authentication': {
            'handlers': ['console', 'security_file'] if not DEBUG else ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        # Legacy API usage tracking for migration monitoring (TD-014)
        'legacy_api': {
            'handlers': ['console', 'security_file'] if not DEBUG else ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# =============================================================================
# PRODUCTION SECURITY VALIDATION
# =============================================================================
# These checks run at startup to ensure critical security settings are configured
if not DEBUG:
    # Check for unchanged default passwords
    _db_password = config('DB_PASSWORD', default='')
    if 'MUST_CHANGE' in _db_password or 'CHANGE' in _db_password or _db_password == 'analytics_pass':
        raise ImproperlyConfigured(
            "DB_PASSWORD must be changed from the default value in production. "
            "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    _redis_password = config('REDIS_PASSWORD', default='')
    if not _redis_password or 'MUST_CHANGE' in _redis_password or 'CHANGE' in _redis_password:
        raise ImproperlyConfigured(
            "REDIS_PASSWORD must be set to a strong value in production. "
            "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    _secret_key = config('SECRET_KEY', default='')
    if 'MUST_CHANGE' in _secret_key or not _secret_key:
        raise ImproperlyConfigured(
            "SECRET_KEY must be set to a secure value in production. "
            "Generate with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\""
        )

    logging.info("Production security validation passed.")
