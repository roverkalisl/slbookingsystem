"""
URL configuration for SL Booking project.

Single-service deployment: Django serves both API and Next.js frontend.
- API routes: /api/*, /admin/, /health/
- Frontend: Everything else falls back to index.html (client-side routing)
"""

import os
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health_check

urlpatterns = [
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

    def serve_frontend(request, path=''):
        """Serve Next.js static export HTML for each route"""
        # Never serve frontend for static files, API, or admin routes - let Django/WhiteNoise handle them
        if path.startswith('static/') or path in ('api',) or path.startswith('api/') or path.startswith('admin/'):
            return HttpResponse('Not found', status=404)

        # For static export, try to serve the route-specific HTML file first
        # Next.js static export generates files like: /register.html, /login.html, /search.html, etc.
        # And nested routes like: /property/0/index.html

        # Route: / → index.html
        if path == '':
            html_file = 'index.html'
        # Route: /some-page → some-page.html OR some-page/index.html
        else:
            # Try direct path first: /login → login.html
            html_file = os.path.join(path + '.html')
            full_path = os.path.join(settings.STATIC_ROOT, html_file)

            if os.path.isfile(full_path):
                try:
                    with open(full_path, 'r') as f:
                        return HttpResponse(f.read(), content_type='text/html')
                except (FileNotFoundError, IOError):
                    pass

            # Try nested path: /property/0 → property/0/index.html
            html_file = os.path.join(path, 'index.html')

        try:
            full_path = os.path.join(settings.STATIC_ROOT, html_file)
            with open(full_path, 'r') as f:
                return HttpResponse(f.read(), content_type='text/html')
        except (FileNotFoundError, IOError):
            # Fallback to index.html if specific route not found
            try:
                index_path = os.path.join(settings.STATIC_ROOT, 'index.html')
                with open(index_path, 'r') as f:
                    return HttpResponse(f.read(), content_type='text/html')
            except FileNotFoundError:
                return HttpResponse('Frontend not built', status=404)

    # Catch-all: Serve index.html for client-side routing
    # This must be LAST in urlpatterns so API routes match first
    urlpatterns += [
        path('', serve_frontend, name='frontend-root'),  # Match / explicitly
        path('<path:path>', serve_frontend),  # Match everything else
    ]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns = [path('__debug__/', include('debug_toolbar.urls'))] + urlpatterns
