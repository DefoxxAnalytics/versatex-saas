"""
Test settings - Uses SQLite for fast, isolated testing
"""
from .settings import *  # noqa: F401, F403

# Use SQLite for testing (faster, no external dependencies)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable password hashing for faster tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable throttling during tests
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}

# Disable Celery during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use local memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# Override production's CompressedManifestStaticFilesStorage (WhiteNoise) with the
# plain StaticFilesStorage. Manifest storage demands collectstatic has populated
# staticfiles.json, which CI skips — admin views then crash with
# "Missing staticfiles manifest entry for 'admin/css/base.css'" on any test that
# renders admin HTML.
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Simplify logging for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
