"""
App configuration for core app.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'

    def ready(self):
        """
        Initialize app - create default roles and settings.
        Skipped during migrations to prevent table access errors.
        """
        import sys
        from .models import Role, SystemSetting

        # Skip initialization during migrations
        # This prevents trying to access tables that don't exist yet
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return

        try:
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
        except Exception:
            # If anything fails (DB not ready, table doesn't exist, etc), just skip
            # The migrations and management commands will handle initialization
            pass
