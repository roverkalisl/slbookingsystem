"""
App configuration for core app.
"""

from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'

    def ready(self):
        """
        Connect post_migrate signal to populate default data.
        This is the recommended Django way - avoid database access in ready().
        """
        # Register post_save handlers (e.g. auto-create UserProfile)
        from . import signals  # noqa: F401

        # Connect the signal handler for post-migration initialization
        post_migrate.connect(self._initialize_defaults, sender=self)

    @staticmethod
    def _initialize_defaults(sender, **kwargs):
        """
        Populate default roles and settings after migrations complete.
        This runs AFTER all migrations have been applied.
        """
        from .models import Role, SystemSetting

        # Create default roles if they don't exist
        role_data = [
            ('super_admin', 'Super Administrator'),
            ('property_owner', 'Property Owner'),
            ('property_staff', 'Property Staff'),
            ('guest', 'Guest'),
        ]

        for role_name, description in role_data:
            Role.objects.get_or_create(
                name=role_name,
                defaults={'description': description}
            )

        # Create default system settings
        default_settings = {
            'DEFAULT_COMMISSION_PERCENTAGE': '7.0',
            'DEFAULT_SERVICE_FEE_PERCENTAGE': '5.0',
            'DEFAULT_TAX_PERCENTAGE': '10.0',
        }

        for key, value in default_settings.items():
            SystemSetting.objects.get_or_create(
                setting_key=key,
                defaults={'setting_value': value}
            )
