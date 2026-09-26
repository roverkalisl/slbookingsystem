"""
URL configuration for SL Booking project.

Single-service deployment: Django serves both API and Next.js frontend.
- API routes: /api/*, /admin/, /health/
- Crawler files: /robots.txt, /sitemap.xml (config/seo.py)
- Frontend: exported pages by path; unknown paths get the exported 404 page
"""

import os
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health_check
from config.adsense import ads_txt
from config.seo import approved_property_for_path, inject_property_seo, robots_txt, sitemap_xml

urlpatterns = [
    # Health check - lightweight, unauthenticated, no DB access.
    # Configure this as Render's Health Check Path.
    path('health/', health_check, name='health-check'),

    # Crawler files - must be matched before the frontend catch-all below
    path('robots.txt', robots_txt, name='robots-txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap-xml'),
    path('ads.txt', ads_txt, name='ads-txt'),

    # Django admin is moved off the /admin path to avoid shadowing the frontend
    # admin dashboard route. Frontend admin pages live under /admin/*.
    path('django-admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),

    # API endpoints
    path('api/auth/', include('apps.core.urls', namespace='auth')),
    path('api/admin/', include('apps.core.admin_urls', namespace='admin')),
    path('api/properties/', include('apps.properties.urls', namespace='properties')),
    path('api/bookings/', include('apps.bookings.urls', namespace='bookings')),
    path('api/reviews/', include('apps.reviews.urls', namespace='reviews')),
    path('api/payments/', include('apps.payments.urls', namespace='payments')),
    path('api/notifications/', include('apps.notifications.urls', namespace='notifications')),
]

# Dynamic Next.js routes. The static export pre-renders each [id] page only
# once, with the placeholder id '0' (see generateStaticParams). Every real
# id - e.g. /property/<uuid> - must be served that shell page; the client
# component then reads the real id from window.location. Without this the
# request fell through to index.html and showed the HOME page instead.
FRONTEND_DYNAMIC_ROUTES = ('property', 'admin/properties')

# Next.js exports its not-found page here; unknown paths are served it with
# HTTP 404 (they used to get the home page with 200 - including /robots.txt,
# /ads.txt and any mistyped URL).
FRONTEND_NOT_FOUND_PAGE = '404.html'


def resolve_frontend_html(path, static_root):
    """
    Return the static-export HTML file (relative to static_root) to serve for
    a frontend path: the page itself, the '0' shell of a dynamic route, or
    the 404 page for anything unknown. None if the frontend is not built.
    """
    path = (path or '').strip('/')
    root = os.path.realpath(static_root)

    if path == '':
        candidates = ['index.html']
    else:
        # /login -> login.html, /nested -> nested/index.html
        candidates = [f'{path}.html', os.path.join(path, 'index.html')]
        parts = path.split('/')
        for prefix in FRONTEND_DYNAMIC_ROUTES:
            prefix_parts = prefix.split('/')
            if len(parts) == len(prefix_parts) + 1 and parts[:-1] == prefix_parts:
                candidates += [f'{prefix}/0.html', f'{prefix}/0/index.html']
        # Unknown route -> the exported not-found page (served with 404)
        candidates.append(FRONTEND_NOT_FOUND_PAGE)

    for candidate in candidates:
        full_path = os.path.realpath(os.path.join(root, candidate))
        # Never serve anything outside the static root (e.g. ../ in the path)
        if not full_path.startswith(root + os.sep):
            continue
        if os.path.isfile(full_path):
            return os.path.relpath(full_path, root)
    return None


def serve_frontend(request, path=''):
    """Serve Next.js static export HTML for each route"""
    # Never serve frontend for static files or API routes.
    # The frontend admin dashboard lives under /admin/* and the Django admin is now at /django-admin/.
    if path.startswith('static/') or path in ('api',) or path.startswith('api/') or path.startswith('django-admin/'):
        return HttpResponse('Not found', status=404)

    html_file = resolve_frontend_html(path, settings.STATIC_ROOT)
    if html_file is None:
        return HttpResponse('Frontend not built', status=404)
    try:
        with open(os.path.join(settings.STATIC_ROOT, html_file), 'r', encoding='utf-8') as f:
            html = f.read()
    except (FileNotFoundError, IOError):
        return HttpResponse('Frontend not built', status=404)

    if html_file.replace(os.sep, '/') == FRONTEND_NOT_FOUND_PAGE:
        return HttpResponse(html, content_type='text/html', status=404)

    # Public property page: property-specific title/description/canonical/OG
    # tags - only for APPROVED properties; anything else gets the generic shell.
    property_obj = approved_property_for_path(path)
    if property_obj is not None:
        html = inject_property_seo(html, property_obj)
    return HttpResponse(html, content_type='text/html')


# PRODUCTION: Serve Next.js frontend via WhiteNoise
# Frontend is built to staticfiles/ and served as a single-page app
if not settings.DEBUG:
    # Catch-all: exported pages (and the 404 page for unknown paths)
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
