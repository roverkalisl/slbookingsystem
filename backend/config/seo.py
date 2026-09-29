"""
Crawler basics and property page SEO for the Next.js static export.

- robots.txt and sitemap.xml are real Django routes (registered before the
  frontend catch-all, which used to answer them with the home page).
- Public property pages (/property/<id>) are one pre-rendered shell with the
  site-wide title; serve_frontend() passes that HTML through
  inject_property_seo() so each APPROVED property gets its own title,
  description, canonical URL, Open Graph / Twitter tags and one Schema.org
  LodgingBusiness JSON-LD block (property_json_ld). Nothing is injected for
  any other property - the generic shell is served unchanged.

All public URLs use settings.CANONICAL_SITE_URL (https://slbooking.hotel.lk),
independent of the host the request arrived on.
"""

import json
import re
from decimal import Decimal
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.utils.html import escape

SITE_NAME = 'SL Booking'
DESCRIPTION_MAX = 160

# Only public, crawl-worthy frontend pages. Owner/admin/login/register/
# booking pages are private or useless to search engines.
SITEMAP_STATIC_PATHS = ['/', '/search', '/about', '/contact', '/privacy', '/terms']
ROBOTS_DISALLOW = ['/owner/', '/admin/', '/django-admin/', '/login', '/register', '/bookings']

# Pages that must never be indexed (X-Robots-Tag: noindex, follow). robots.txt
# still disallows them as before; the header covers URLs found via links.
NOINDEX_PATH_PREFIXES = ('admin', 'owner', 'login', 'register', 'bookings', 'booking')
NOINDEX_FOLLOW = 'noindex, follow'
# (Title/description/canonical/Open Graph for the home, search, about, contact,
# privacy and terms pages come from Next.js metadata in the static export -
# frontend/src/app/**/page.tsx. Django only adds page-specific tags for
# approved property pages, which are one shared pre-rendered shell.)


def robots_header_for(path: str, query_string: str = ''):
    """'noindex, follow' for private pages and filtered search URLs; None when indexable."""
    clean = (path or '').strip('/')
    first = clean.split('/', 1)[0].lower()
    if first in NOINDEX_PATH_PREFIXES:
        return NOINDEX_FOLLOW
    # /search is indexable; /search?destination=... (any query) is not - canonical is /search
    if clean == 'search' and query_string:
        return NOINDEX_FOLLOW
    return None


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


# ---------------------------------------------------------------- structured data (Schema.org JSON-LD)

JSON_LD_MAX_IMAGES = 10
JSON_LD_DESCRIPTION_MAX = 5000
# The platform only lists Sri Lankan properties (the owner form's Country is fixed to Sri Lanka)
COUNTRY_CODE = 'LK'
# Never publish image URLs pointing at non-public hosts
_NON_PUBLIC_HOSTS = ('localhost', '127.0.0.1', '0.0.0.0', 'onrender.com')


def _public_image_url(url):
    """A real, public https image URL (e.g. res.cloudinary.com), else None."""
    if not url or not isinstance(url, str):
        return None
    parsed = urlparse(url.strip())
    host = (parsed.hostname or '').lower()
    if parsed.scheme != 'https' or not host or any(host == h or host.endswith('.' + h) for h in _NON_PUBLIC_HOSTS):
        return None
    return url.strip()


def _lkr(amount: Decimal) -> str:
    return f'LKR {amount:,.0f}' if amount == amount.to_integral_value() else f'LKR {amount:,.2f}'


def _price_range(property_obj):
    """
    Nightly base price(s) of the bookable room types - the same base prices the
    public page shows ("Starting from ..."). No fees, taxes or seasonal rates.
    """
    from apps.properties.models import Pricing
    from apps.properties.serializers import bookable_room_types_of

    prices = sorted({
        price for price in Pricing.objects.filter(room_type__in=bookable_room_types_of(property_obj))
        .values_list('base_price', flat=True) if price is not None and price > 0
    })
    if not prices:
        return None
    low, high = prices[0], prices[-1]
    return _lkr(low) if low == high else f'{_lkr(low)} - {_lkr(high)}'


def _aggregate_rating(property_obj):
    """
    From real public guest reviews only; None when there are none. Uses the
    same eligibility rules and rounding as the rating shown on the page
    (apps.reviews.ratings), so the two can never disagree.
    """
    from apps.reviews.ratings import MAX_RATING, MIN_RATING, public_rating

    average, count = public_rating(property_obj.pk)
    if average is None:
        return None
    return {
        '@type': 'AggregateRating',
        'ratingValue': average,
        'reviewCount': count,
        'bestRating': MAX_RATING,
        'worstRating': MIN_RATING,
    }


def property_json_ld(property_obj) -> dict:
    """
    Schema.org LodgingBusiness for an APPROVED property, built only from real,
    already-public listing data. Optional fields are omitted when empty -
    never null, never invented. No owner, contact, booking or guest data.
    """
    url = property_url(property_obj.id)
    data = {
        '@context': 'https://schema.org',
        '@type': 'LodgingBusiness',
        '@id': f'{url}#lodging',
        'name': property_obj.name,
        'url': url,
    }

    description = _plain_text(property_obj.description) or _plain_text(property_obj.short_description)
    if description:
        data['description'] = description[:JSON_LD_DESCRIPTION_MAX]

    # Cover photo first, then the rest in display order (same order as the gallery)
    photos = sorted(property_obj.photos.all(), key=lambda p: (not p.is_cover, p.display_order, p.created_at))
    images = []
    for photo in photos:
        image = _public_image_url(photo.cloudinary_url)
        if image and image not in images:
            images.append(image)
    if images:
        data['image'] = images[:JSON_LD_MAX_IMAGES]

    # Only the location the public page shows: city and region. No street address,
    # postal code or coordinates.
    address = {'@type': 'PostalAddress'}
    if _plain_text(property_obj.city):
        address['addressLocality'] = _plain_text(property_obj.city)
    if _plain_text(property_obj.province):
        address['addressRegion'] = _plain_text(property_obj.province)
    if len(address) > 1:
        address['addressCountry'] = COUNTRY_CODE
        data['address'] = address

    amenities = [pa.amenity.name for pa in property_obj.propertyamenity_set.select_related('amenity').order_by('amenity__name')
                 if pa.amenity.is_active and _plain_text(pa.amenity.name)]
    if amenities:
        data['amenityFeature'] = [
            {'@type': 'LocationFeatureSpecification', 'name': name, 'value': True} for name in amenities
        ]

    price_range = _price_range(property_obj)
    if price_range:
        data['priceRange'] = price_range

    rating = _aggregate_rating(property_obj)
    if rating:
        data['aggregateRating'] = rating
    return data


def json_ld_script(data: dict) -> str:
    """<script type="application/ld+json"> safe to embed in HTML (no </script> break-out)."""
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    payload = payload.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    return f'<script type="application/ld+json">{payload}</script>'


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


# Tags the page-specific metadata replaces. The Next.js export puts site-wide
# defaults (og:*, twitter:*) into every page; they are removed first so each
# tag appears exactly once.
_REPLACED_TAG_PATTERNS = [
    r'<link rel="canonical"[^>]*>',
    r'<meta property="og:(?:title|description|url|type|site_name)"[^>]*>',
    r'<meta name="twitter:(?:card|title|description)"[^>]*>',
]
_IMAGE_TAG_PATTERNS = [r'<meta property="og:image(?::[a-z_]+)?"[^>]*>', r'<meta name="twitter:image(?::[a-z_]+)?"[^>]*>']


def _has_default_image(html: str) -> bool:
    return re.search(_IMAGE_TAG_PATTERNS[0], html) is not None


def set_head_metadata(html: str, *, title: str, description: str, url: str, og_type: str = 'website',
                      image: str = None, extra_tags=()) -> str:
    """
    Page-specific <title>, description, canonical, Open Graph and Twitter tags,
    each exactly once. `image` (an absolute https URL) replaces the site-wide
    default Open Graph image; without it the default image stays.
    """
    title, description, url = escape(title), escape(description), escape(url)
    html = re.sub(r'<title>.*?</title>', f'<title>{title}</title>', html, count=1, flags=re.S)
    description_tag = f'<meta name="description" content="{description}"/>'
    html, replaced = re.subn(r'<meta name="description" content="[^"]*"\s*/?>', description_tag, html, count=1)
    for pattern in _REPLACED_TAG_PATTERNS + (_IMAGE_TAG_PATTERNS if image else []):
        html = re.sub(pattern, '', html)

    tags = [] if replaced else [description_tag]
    tags += [
        f'<link rel="canonical" href="{url}"/>',
        f'<meta property="og:type" content="{og_type}"/>',
        f'<meta property="og:site_name" content="{SITE_NAME}"/>',
        f'<meta property="og:title" content="{title}"/>',
        f'<meta property="og:description" content="{description}"/>',
        f'<meta property="og:url" content="{url}"/>',
        f'<meta name="twitter:card" content="{"summary_large_image" if image or _has_default_image(html) else "summary"}"/>',
        f'<meta name="twitter:title" content="{title}"/>',
        f'<meta name="twitter:description" content="{description}"/>',
    ]
    if image:
        image = escape(image)
        tags += [f'<meta property="og:image" content="{image}"/>', f'<meta name="twitter:image" content="{image}"/>']
    tags += list(extra_tags)
    return html.replace('</head>', ''.join(tags) + '</head>', 1)


def inject_property_seo(html: str, property_obj) -> str:
    """Property-specific <title>, description, canonical, Open Graph / Twitter tags and JSON-LD."""
    from apps.properties.serializers import cover_url_of

    image = cover_url_of(property_obj)
    extra = []
    # Exactly one structured-data block per approved property page
    if 'application/ld+json' not in html:
        extra.append(json_ld_script(property_json_ld(property_obj)))
    return set_head_metadata(
        html, title=page_title(property_obj), description=meta_description(property_obj),
        url=property_url(property_obj.id), image=image if image and image.startswith('https://') else None,
        extra_tags=extra,
    )
