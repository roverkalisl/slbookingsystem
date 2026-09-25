"""
Crawler basics and property page SEO for the Next.js static export.

- robots.txt and sitemap.xml are real Django routes (registered before the
  frontend catch-all, which used to answer them with the home page).
- Public property pages (/property/<id>) are one pre-rendered shell with the
  site-wide title; serve_frontend() passes that HTML through
  inject_property_seo() so each APPROVED property gets its own title,
  description, canonical URL and Open Graph / Twitter tags. Nothing is
  injected for any other property - the generic shell is served unchanged.

All public URLs use settings.CANONICAL_SITE_URL (https://slbooking.hotel.lk),
independent of the host the request arrived on.
"""

import re
from xml.sax.saxutils import escape as xml_escape

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils.html import escape

SITE_NAME = 'SL Booking'
DESCRIPTION_MAX = 160

# Only public, crawl-worthy frontend pages. Owner/admin/login/register/
# booking pages are private or useless to search engines.
SITEMAP_STATIC_PATHS = ['/', '/search']
ROBOTS_DISALLOW = ['/owner/', '/admin/', '/django-admin/', '/login', '/register', '/bookings']


def canonical_base() -> str:
    return settings.CANONICAL_SITE_URL.rstrip('/')


def property_url(property_id) -> str:
    return f'{canonical_base()}/property/{property_id}'


# ---------------------------------------------------------------- robots / sitemap

def robots_txt(request):
    # /api/ is deliberately NOT disallowed: search engines render the property
    # page, which loads its content from the public API.
    lines = ['User-agent: *', 'Allow: /']
    lines += [f'Disallow: {path}' for path in ROBOTS_DISALLOW]
    lines += ['', f'Sitemap: {canonical_base()}/sitemap.xml', '']
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')


def sitemap_xml(request):
    from apps.properties.models import Property

    entries = [(f'{canonical_base()}{path}', None) for path in SITEMAP_STATIC_PATHS]
    approved = Property.objects.filter(status='approved').order_by('-updated_at').values_list('id', 'updated_at')
    entries += [(property_url(pid), updated.date().isoformat() if updated else None) for pid, updated in approved]

    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in entries:
        body.append('  <url>')
        body.append(f'    <loc>{xml_escape(loc)}</loc>')
        if lastmod:
            body.append(f'    <lastmod>{lastmod}</lastmod>')
        body.append('  </url>')
    body.append('</urlset>')
    return HttpResponse('\n'.join(body) + '\n', content_type='application/xml; charset=utf-8')


# ---------------------------------------------------------------- property page metadata

def _plain_text(value: str) -> str:
    return re.sub(r'\s+', ' ', value or '').strip()


def meta_description(property_obj) -> str:
    """The property's own text (short description, else description), trimmed to ~160 chars."""
    text = _plain_text(property_obj.short_description) or _plain_text(property_obj.description)
    if not text:
        location = ', '.join(part for part in (property_obj.city, property_obj.district) if part)
        text = f'{property_obj.name} in {location}, Sri Lanka.' if location else property_obj.name
    if len(text) > DESCRIPTION_MAX:
        cut = text[:DESCRIPTION_MAX - 1].rsplit(' ', 1)[0].rstrip(' ,.;:-')
        text = f'{cut}…'
    return text


def page_title(property_obj) -> str:
    place = property_obj.city
    return f'{property_obj.name} - {place} | {SITE_NAME}' if place else f'{property_obj.name} | {SITE_NAME}'


def approved_property_for_path(path: str):
    """The approved Property for a /property/<id> page path, else None."""
    from apps.properties.models import Property

    parts = (path or '').strip('/').split('/')
    if len(parts) != 2 or parts[0] != 'property' or parts[1] in ('', '0'):
        return None
    try:
        return Property.objects.filter(pk=parts[1], status='approved').first()
    except (ValueError, ValidationError):
        return None


def inject_property_seo(html: str, property_obj) -> str:
    """Property-specific <title>, description, canonical, Open Graph and Twitter tags."""
    from apps.properties.serializers import cover_url_of

    title = escape(page_title(property_obj))
    description = escape(meta_description(property_obj))
    url = escape(property_url(property_obj.id))
    image = cover_url_of(property_obj)
    image = escape(image) if image and image.startswith('https://') else None

    html = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', html, count=1, flags=re.S)
    description_tag = f'<meta name="description" content="{description}"/>'
    html, replaced = re.subn(r'<meta name="description" content="[^"]*"\s*/?>', description_tag, html, count=1)
    extra = [] if replaced else [description_tag]

    extra += [
        f'<link rel="canonical" href="{url}"/>',
        f'<meta property="og:type" content="website"/>',
        f'<meta property="og:site_name" content="{SITE_NAME}"/>',
        f'<meta property="og:title" content="{title}"/>',
        f'<meta property="og:description" content="{description}"/>',
        f'<meta property="og:url" content="{url}"/>',
        f'<meta name="twitter:card" content="{"summary_large_image" if image else "summary"}"/>',
        f'<meta name="twitter:title" content="{title}"/>',
        f'<meta name="twitter:description" content="{description}"/>',
    ]
    if image:
        extra += [f'<meta property="og:image" content="{image}"/>', f'<meta name="twitter:image" content="{image}"/>']
    return html.replace('</head>', ''.join(extra) + '</head>', 1)
