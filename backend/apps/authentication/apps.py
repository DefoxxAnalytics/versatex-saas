from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.authentication'
    verbose_name = 'Authentication'

    def ready(self):
        # Import schema extensions to register them with drf-spectacular
        try:
            from . import schema  # noqa: F401
        except ImportError:
            pass
