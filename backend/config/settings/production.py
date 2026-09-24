"""
Production settings for SL Booking - Phase 7 Deployment.

Security, performance, monitoring, and resilience configured for production.
This is an enterprise-grade configuration for the accommodation marketplace.

Key Features:
- HTTPS/TLS enforcement
- Rate limiting (100 req/hr anonymous, 1000 req/hr authenticated)
- Redis caching (sessions, search filters)
- Sentry error tracking
- Database connection pooling
- Async task queue (Celery)
- Secure cookie settings
- CSP headers for XSS prevention
- Gzip compression for responses
"""

import os
from pathlib import Path
from datetime import timedelta
from decouple import config, Csv
import dj_database_url

from .common import *  # noqa

# ============================================================================
# CRITICAL SECURITY SETTINGS
# ============================================================================

DEBUG = False

# Secret key MUST be in environment
SECRET_KEY = config('SECRET_KEY')
if not SECRET_KEY or len(SECRET_KEY) < 50:
    raise ValueError("SECRET_KEY must be set and at least 50 characters")

# Allowed hosts - configure with your domains
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='slbookingsystem.onrender.com,slbooking.hotel.lk,www.slbooking.hotel.lk',
    cast=Csv(),
)

# CSRF_TRUSTED_ORIGINS: required by Django 4+ for any cross-scheme/cross-port
# POST (admin login, forms, DRF browsable API) to pass CSRF verification when
# the app sits behind a reverse proxy like Render's edge. Must include scheme.
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://slbookingsystem.onrender.com,https://slbookingsystem-frontend.onrender.com,https://slbooking.hotel.lk,https://www.slbooking.hotel.lk',
    cast=Csv()
)

# Render (and most PaaS) terminate TLS at the edge and forward plain HTTP to
# the app, setting X-Forwarded-Proto: https. Without telling Django to trust
# that header, request.is_secure() is always False behind the proxy, and
# SECURE_SSL_REDIRECT below causes an INFINITE REDIRECT LOOP (Django keeps
# "redirecting to HTTPS" on a request that already arrived via HTTPS).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Secure cookies - HTTPS only
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# HTTPS redirect
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r'^health/?$', r'^status/?$']  # Health checks don't redirect

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Clickjacking protection
X_FRAME_OPTIONS = 'DENY'

# Browser XSS protection
SECURE_BROWSER_XSS_FILTER = True

# Content Security Policy (XSS prevention)
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"),
    'style-src': ("'self'", "https://fonts.googleapis.com", "'unsafe-inline'"),
    'font-src': ("'self'", "https://fonts.gstatic.com"),
    'img-src': ("'self'", "data:", "https:", "https://res.cloudinary.com"),
    'media-src': ("'self'", "https:",),
    'connect-src': ("'self'", "https:", "wss:", "https://api.stripe.com"),
    'object-src': ("'none'",),
    'frame-ancestors': ("'none'",),
    'base-uri': ("'self'",),
}

# ============================================================================
# DATABASE - POSTGRESQL WITH CONNECTION POOLING
# ============================================================================

# Use Render's DATABASE_URL if available, otherwise fall back to individual variables
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    # Parse DATABASE_URL from Render PostgreSQL
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,  # Connection pooling (10 min)
            conn_health_checks=True,
        )
    }
    # Add options after parsing
    DATABASES['default']['OPTIONS'] = {
        'connect_timeout': 10,
    }
else:
    # Fallback to individual environment variables (for other deployments)
    # Note: Render uses DATABASE_URL, so this is for manual deployments only
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='slbooking'),
            'USER': config('DB_USER', default='slbooking_user'),
            'PASSWORD': config('DB_PASSWORD', default=''),  # Required in actual use, empty for testing
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432', cast=int),
            'CONN_MAX_AGE': 600,
            'OPTIONS': {
                'connect_timeout': 10,
            }
        }
    }

# ============================================================================
# CACHING - REDIS FOR PERFORMANCE (with safe fallback if Redis not provisioned)
# ============================================================================

# REDIS_URL is only set when a Redis service is attached on Render.
# If it's absent, we MUST NOT default to a localhost URL that doesn't exist -
# that would make every request needing cache/session (e.g. login) fail with
# a connection error. Fall back to safe, dependency-free backends instead.
REDIS_URL = config('REDIS_URL', default='')

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {'max_connections': 50, 'retry_on_timeout': True},
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            },
            'KEY_PREFIX': 'slbooking',
            'TIMEOUT': 300,  # 5 minutes default
        }
    }
    # Session backend via Redis (faster than database)
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # No Redis provisioned - use safe fallbacks with zero external dependencies.
    # Site remains fully functional (login, search, etc.); only loses the
    # performance boost from Redis until a Redis service is attached.
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'slbooking-local-fallback-cache',
        }
    }
    # Database-backed sessions - always available, no external service needed
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ============================================================================
# EMAIL - SENDGRID FOR RELIABLE DELIVERY
# ============================================================================

EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
SENDGRID_API_KEY = config('SENDGRID_API_KEY', default='')

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@slbooking.hotel.lk')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

EMAIL_TIMEOUT = 10

# ============================================================================
# STATIC & MEDIA FILES
# ============================================================================

# Static files with WhiteNoise (serves from disk, gzipped)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files via Cloudinary (optional - defaults to local storage if not configured)
# Preferred: a single CLOUDINARY_URL env var (cloudinary://key:secret@cloud_name),
# which the cloudinary SDK parses automatically. Individual vars are still
# supported as a fallback for compatibility.
CLOUDINARY_URL_CONFIGURED = config('CLOUDINARY_URL', default='')
CLOUDINARY_CLOUD_NAME = config('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY = config('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = config('CLOUDINARY_API_SECRET', default='')

CLOUDINARY_CONFIGURED = bool(CLOUDINARY_URL_CONFIGURED or CLOUDINARY_CLOUD_NAME)

if CLOUDINARY_CONFIGURED:
    # cloudinary_storage/cloudinary packages are only required (and only
    # imported) when Cloudinary is actually configured - see requirements.txt
    INSTALLED_APPS = INSTALLED_APPS + ['cloudinary_storage', 'cloudinary']  # noqa: F405

    if CLOUDINARY_CLOUD_NAME:
        # Explicit individual credentials take precedence if provided
        CLOUDINARY_STORAGE = {
            'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
            'API_KEY': CLOUDINARY_API_KEY,
            'API_SECRET': CLOUDINARY_API_SECRET,
        }
    # else: CLOUDINARY_URL is present in the environment and the cloudinary
    # SDK reads it automatically - no CLOUDINARY_STORAGE dict needed.

    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
else:
    # Fallback to local media storage (create media/ directory)
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

MEDIA_URL = '/media/'

# ============================================================================
# COMPRESSION & PERFORMANCE
# ============================================================================

# Gzip compression for responses
MIDDLEWARE.insert(0, 'django.middleware.gzip.GZipMiddleware')  # noqa

# WhiteNoise middleware for static files
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')  # noqa

# Template caching
# APP_DIRS: True in common.py handles template discovery
# Custom loaders removed to prevent conflict with APP_DIRS

# ============================================================================
# LOGGING - SENTRY + LOCAL FILES
# ============================================================================

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

SENTRY_DSN = config('SENTRY_DSN', default='')

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            RedisIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        send_default_pii=False,  # Never send PII to Sentry
        environment=config('ENVIRONMENT', default='production'),
        release=config('RELEASE_VERSION', default='1.0.0'),
    )

# File-based logging with rotation
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# ============================================================================
# CELERY - ASYNC TASKS
# ============================================================================

CELERY_BROKER_URL = REDIS_URL or 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = REDIS_URL or 'redis://127.0.0.1:6379/0'

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit
CELERY_RESULT_EXPIRES = 3600  # 1 hour

# If no Redis is provisioned, there's no broker to talk to. Run tasks
# synchronously (in-process) instead of trying to connect and failing -
# notifications/webhooks still execute, just without async queuing.
if not REDIS_URL:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# Task routing for different queue priorities
CELERY_TASK_ROUTING = {
    'apps.notifications.tasks.send_email': {'queue': 'email', 'routing_key': 'email'},
    'apps.notifications.tasks.send_sms': {'queue': 'sms', 'routing_key': 'sms'},
    'apps.payments.tasks.process_webhook': {'queue': 'payments', 'routing_key': 'payments'},
}

# ============================================================================
# API RATE LIMITING - PREVENT ABUSE
# ============================================================================

REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = [  # noqa
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
]

REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {  # noqa
    'anon': '100/hour',          # 100 requests/hour for anonymous
    'user': '1000/hour',         # 1000 requests/hour for authenticated
    'booking': '10/hour',        # 10 bookings/hour per user
    'payment': '50/hour',        # 50 payment attempts/hour
    'search': '200/hour',        # 200 searches/hour
}

# Disable format suffix patterns to prevent converter registration conflicts
REST_FRAMEWORK['FORMAT_SUFFIX_PATTERNS'] = False  # noqa

# ============================================================================
# JWT AUTHENTICATION - PRODUCTION
# ============================================================================

SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'] = timedelta(hours=1)  # noqa
SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'] = timedelta(days=7)  # noqa
SIMPLE_JWT['ROTATE_REFRESH_TOKENS'] = True  # noqa
SIMPLE_JWT['BLACKLIST_AFTER_ROTATION'] = True  # noqa
SIMPLE_JWT['ALGORITHM'] = 'HS256'  # noqa
SIMPLE_JWT['SIGNING_KEY'] = SECRET_KEY  # noqa

# ============================================================================
# PAYMENT GATEWAYS - PRODUCTION CREDENTIALS
# ============================================================================

# Stripe settings (STRIPE_LIVE_SECRET_KEY, STRIPE_WEBHOOK_SECRET,
# STRIPE_LIVE_PUBLIC_KEY, SITE_URL) are defined in common.py from the
# environment, so development/test use the same names.

# ============================================================================
# THIRD-PARTY SERVICES
# ============================================================================

# Twilio SMS
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_PHONE_NUMBER = config('TWILIO_PHONE_NUMBER', default='')

# Firebase Push Notifications
FIREBASE_SERVICE_ACCOUNT = config('FIREBASE_SERVICE_ACCOUNT', default='')

# ============================================================================
# CORS - FRONTEND DOMAINS
# ============================================================================

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='https://slbookingsystem-frontend.onrender.com,https://slbooking.hotel.lk,https://www.slbooking.hotel.lk',
    cast=Csv()
)

CORS_ALLOW_CREDENTIALS = True

# ============================================================================
# SECURITY HEADERS
# ============================================================================

MIDDLEWARE.extend([  # noqa
    'django.middleware.security.SecurityMiddleware',
])

# ============================================================================
# DJANGO 4.2+ ASYNC SETTINGS
# ============================================================================

ASGI_TIMEOUT_KEEP_ALIVE = 20

# ============================================================================
# PERFORMANCE TESTING & MONITORING
# ============================================================================

# Disable SQL query logging in production
LOGGING_SQL_QUERIES = False

# Enable query result caching
ENABLE_QUERY_CACHING = True

# Cache search results for 30 minutes
SEARCH_CACHE_TIMEOUT = 1800

# ============================================================================
# LOGGING NOTES
# ============================================================================
# Production logging uses console/stdout handler.
# Render captures all stdout/stderr in service logs.
# No file-based logging in production (read-only filesystem on Render).
