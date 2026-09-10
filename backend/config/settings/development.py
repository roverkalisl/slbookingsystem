"""
Development settings for SL Booking.
"""

from .common import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Add debug toolbar
INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# Disable email in development (use console backend)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Simple JWT - longer token lifetime for development
SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(hours=24)

# Celery - use eager mode in development
CELERY_TASK_ALWAYS_EAGER = True

# Allow all CORS origins in development
CORS_ALLOW_ALL_ORIGINS = True
