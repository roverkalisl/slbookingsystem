"""
URL configuration for SL Booking project.

Single-service deployment: Django serves both API and Next.js frontend.
- API routes: /api/*, /admin/, /health/
- Frontend: Everything else falls back to index.html (client-side routing)
"""

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health_check

urlpatterns = [
    # API root - keep the backend URL useful when opened directly.
    path('', health_check, name='api-root'),

    # Health check - lightweight, unauthenticated, no DB access.
    # Configure this as Render's Health Check Path.
    path('health/', health_check, name='health-check'),

    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),

    # API endpoints
    path('api/auth/', include('apps.core.urls', namespace='auth')),
    path('api/properties/', include('apps.properties.urls', namespace='properties')),
    path('api/bookings/', include('apps.bookings.urls', namespace='bookings')),
    path('api/reviews/', include('apps.reviews.urls', namespace='reviews')),
    path('api/payments/', include('apps.payments.urls', namespace='payments')),
    path('api/notifications/', include('apps.notifications.urls', namespace='notifications')),
]

# PRODUCTION: Serve Next.js frontend via WhiteNoise
# Frontend is built to staticfiles/ and served as a single-page app
if not settings.DEBUG:
    from django.http import HttpResponse
    from django.views.decorators.http import condition

    def serve_frontend(request, path=''):
        """Serve Next.js frontend index.html for client-side routing"""
        try:
            with open(settings.STATIC_ROOT / 'index.html', 'r') as f:
                return HttpResponse(f.read(), content_type='text/html')
        except FileNotFoundError:
            return HttpResponse('Frontend not built', status=404)

    # Catch-all: Serve index.html for client-side routing
    # This must be LAST in urlpatterns so API routes match first
    urlpatterns += [
        path('<path:path>', serve_frontend),
    ]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns = [path('__debug__/', include('debug_toolbar.urls'))] + urlpatterns
