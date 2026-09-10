"""
Production settings for SL Booking.
"""

from .common import *

DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='slbooking.hotel.lk', cast=Csv())

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net"),
    'style-src': ("'self'", "'unsafe-inline'", "fonts.googleapis.com"),
    'img-src': ("'self'", "data:", "https:", "https://res.cloudinary.com"),
    'font-src': ("'self'", "fonts.gstatic.com"),
    'connect-src': ("'self'", "*.slbooking.hotel.lk"),
}

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Sentry error tracking
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=config('SENTRY_DSN', default=''),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False
)

# Database
DATABASES['default']['CONN_MAX_AGE'] = 600

# Static files - WhiteNoise for serving static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Email - use SendGrid or Gmail
EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'

# CORS - whitelist specific domains
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='https://slbooking.hotel.lk',
    cast=Csv()
)

# Logging - file-based
LOGGING['handlers']['file']['filename'] = '/var/log/slbooking/django.log'
