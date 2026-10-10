from django.apps import AppConfig


class RestaurantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "restaurants"

    def ready(self):
        # Register the SQLite function on every connection, including tests.
        from . import search  # noqa: F401
