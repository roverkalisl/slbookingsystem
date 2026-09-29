from django.apps import AppConfig

class ReviewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reviews'

    def ready(self):
        # Keeps Property.average_rating / total_reviews in sync with public reviews
        from . import signals  # noqa: F401
