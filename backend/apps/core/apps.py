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
