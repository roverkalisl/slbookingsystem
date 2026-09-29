"""
SEO Phase 1: noindex for private pages and filtered searches, home/search
metadata, /search/ -> /search, root brand assets (favicon, icons, default OG
image), one set of social tags per page, sitemap and robots.txt.

Requests go through the real URLconf (the production frontend catch-all is
active under the test runner, DEBUG=False).

Run with: python manage.py test config.tests_seo_phase1
"""

import json
import os
import re
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.properties.models import Property, PropertyPhoto, PropertyType

User = get_user_model()
CANONICAL = 'https://slbooking.hotel.lk'

# Same shape as the real export: site-wide defaults from the root layout metadata
DEFAULT_HEAD = (
    '<title>SL Booking - Sri Lankan Accommodation Marketplace</title>'
    '<meta name="description" content="Book accommodations across Sri Lanka - Villas, Apartments, Resorts"/>'
    '<meta property="og:title" content="SL Booking - Sri Lankan Accommodation Marketplace"/>'
    '<meta property="og:description" content="Book accommodations across Sri Lanka - Villas, Apartments, Resorts"/>'
    '<meta property="og:site_name" content="SL Booking"/>'
    f'<meta property="og:image" content="{CANONICAL}/og-default.png"/>'
    '<meta property="og:image:width" content="1200"/><meta property="og:image:height" content="630"/>'
    '<meta property="og:image:alt" content="SL Booking"/><meta property="og:type" content="website"/>'
    '<meta name="twitter:card" content="summary_large_image"/>'
    '<meta name="twitter:title" content="SL Booking - Sri Lankan Accommodation Marketplace"/>'
    '<meta name="twitter:description" content="Book accommodations across Sri Lanka - Villas, Apartments, Resorts"/>'
    f'<meta name="twitter:image" content="{CANONICAL}/og-default.png"/>'
    '<link rel="icon" href="/favicon.ico"/>'
)
PAGES = ['login.html', 'register.html', 'bookings.html', 'about.html',
         'admin/dashboard.html', 'owner/dashboard.html', 'property/0.html']


def next_page_head(title, description, path):
    """Head of a page with its own Next.js metadata (home, search) - as in the real export."""
    url = f'{CANONICAL}{path}'
    return (
        f'<title>{title}</title><meta name="description" content="{description}"/>'
        f'<link rel="canonical" href="{url}"/>'
        f'<meta property="og:title" content="{title}"/><meta property="og:description" content="{description}"/>'
        f'<meta property="og:url" content="{url}"/><meta property="og:site_name" content="SL Booking"/>'
        f'<meta property="og:image" content="{CANONICAL}/og-default.png"/><meta property="og:type" content="website"/>'
        f'<meta name="twitter:card" content="summary_large_image"/><meta name="twitter:title" content="{title}"/>'
        f'<meta name="twitter:description" content="{description}"/>'
        f'<meta name="twitter:image" content="{CANONICAL}/og-default.png"/>'
    )


EXPORTED_PAGES = {
    'index.html': next_page_head('SL Booking | Villas, Hotels &amp; Holiday Homes in Sri Lanka', 'Search and book villas', '/'),
    'search.html': next_page_head('Search Accommodation in Sri Lanka | SL Booking', 'Search villas', '/search'),
}
NOT_FOUND = '<html><head><meta name="robots" content="noindex"/><title>404</title></head><body>404</body></html>'


def tags(html, pattern):
    return re.findall(pattern, html)


@override_settings(CANONICAL_SITE_URL=CANONICAL)
class SeoPhase1TestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        for name in PAGES:
            path = os.path.join(self.tmp.name, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f'<!DOCTYPE html><html lang="en"><head>{DEFAULT_HEAD}</head><body>{name}</body></html>')
        for name, head in EXPORTED_PAGES.items():
            with open(os.path.join(self.tmp.name, name), 'w', encoding='utf-8') as f:
                f.write(f'<!DOCTYPE html><html lang="en"><head>{head}</head><body>{name}</body></html>')
        with open(os.path.join(self.tmp.name, '404.html'), 'w', encoding='utf-8') as f:
            f.write(NOT_FOUND)
        for name, data in (('favicon.ico', b'\x00\x00\x01\x00ico'), ('icon.svg', b'<svg xmlns="http://www.w3.org/2000/svg"/>'),
                           ('apple-icon.png', b'\x89PNG apple'), ('og-default.png', b'\x89PNG og'),
                           ('secret.html', b'<html>not an asset</html>')):
            with open(os.path.join(self.tmp.name, name), 'wb') as f:
                f.write(data)
        self.static = override_settings(STATIC_ROOT=self.tmp.name)
        self.static.enable()

        owner = User.objects.create_user(email='p1-owner@example.com', password='x')
        ptype = PropertyType.objects.create(name='P1 Villa')
        make = lambda name, status: Property.objects.create(
            owner=owner, property_type=ptype, name=name, status=status, description='A lovely villa near the beach.',
            city='Galle', district='Galle', province='Southern')
        self.approved = make('Sea Breeze Villa', 'approved')
        PropertyPhoto.objects.create(property=self.approved, is_cover=True, cloudinary_public_id='c',
                                     cloudinary_url='https://res.cloudinary.com/demo/sea-breeze.jpg')
        self.no_photo = make('Photo-less Villa', 'approved')
        self.pending = make('Pending Villa', 'pending_approval')

    def tearDown(self):
        self.static.disable()
        self.tmp.cleanup()

    # ---------------------------------------------------------------- 1. noindex

    def test_private_pages_are_noindex_follow(self):
        for url in ('/admin/dashboard', '/owner/dashboard', '/login', '/register', '/bookings', '/booking/abc'):
            response = self.client.get(url)
            self.assertEqual(response['X-Robots-Tag'], 'noindex, follow', url)

    def test_public_pages_are_indexable(self):
        for url in ('/', '/search', f'/property/{self.approved.id}', '/about'):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertFalse(response.has_header('X-Robots-Tag'), url)
            self.assertNotIn('noindex', response.content.decode(), url)

    # ---------------------------------------------------------------- 2/3. home and search
    # (their tags come from Next.js metadata in the export; Django must pass them through untouched)

    def test_home_and_search_metadata_served_from_the_export_unchanged(self):
        for url, name in (('/', 'index.html'), ('/search', 'search.html')):
            html = self.client.get(url).content.decode()
            self.assertIn(EXPORTED_PAGES[name], html, url)
            self.assertSingleSocialTags(html)
        self.assertIn('<link rel="canonical" href="https://slbooking.hotel.lk/"/>', self.client.get('/').content.decode())

    def test_filtered_search_urls_are_noindex_with_canonical_search(self):
        for query in ('destination=Galle', 'check_in=2026-12-01&check_out=2026-12-04', 'guests=4'):
            response = self.client.get(f'/search?{query}')
            self.assertEqual(response.status_code, 200, query)
            self.assertEqual(response['X-Robots-Tag'], 'noindex, follow', query)
            html = response.content.decode()
            self.assertIn('<link rel="canonical" href="https://slbooking.hotel.lk/search"/>', html)
            # header only - no robots meta, so public search pages stay eligible for AdSense
            self.assertNotIn('name="robots"', html)

    def test_search_trailing_slash_redirects(self):
        response = self.client.get('/search/')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/search')
        response = self.client.get('/search/?destination=Galle&guests=2')
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], '/search?destination=Galle&guests=2')
        self.assertEqual(self.client.get('/admin/dashboard/')['Location'], '/admin/dashboard')
        self.assertEqual(self.client.get('/')['Content-Type'], 'text/html')  # root is not redirected

    # ---------------------------------------------------------------- 4. property pages keep their SEO

    def test_approved_property_keeps_real_image_and_single_tags(self):
        response = self.client.get(f'/property/{self.approved.id}')
        html = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn('<title>Sea Breeze Villa - Galle | SL Booking</title>', html)
        self.assertIn(f'<link rel="canonical" href="{CANONICAL}/property/{self.approved.id}"/>', html)
        self.assertEqual(tags(html, r'<meta property="og:image" content="([^"]*)"'), ['https://res.cloudinary.com/demo/sea-breeze.jpg'])
        self.assertEqual(tags(html, r'<meta name="twitter:image" content="([^"]*)"'), ['https://res.cloudinary.com/demo/sea-breeze.jpg'])
        self.assertNotIn('og:image:width', html)  # default image's extra tags removed with it
        self.assertSingleSocialTags(html)
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(json.loads(blocks[0])['@type'], 'LodgingBusiness')

    def test_property_without_photo_falls_back_to_the_default_image(self):
        html = self.client.get(f'/property/{self.no_photo.id}').content.decode()
        self.assertEqual(tags(html, r'<meta property="og:image" content="([^"]*)"'), [f'{CANONICAL}/og-default.png'])
        self.assertSingleSocialTags(html)

    def test_unapproved_property_gets_the_generic_shell(self):
        html = self.client.get(f'/property/{self.pending.id}').content.decode()
        self.assertNotIn('Pending Villa', html)
        self.assertNotIn('application/ld+json', html)

    # ---------------------------------------------------------------- 5/6. favicon, icons, OG image

    def test_brand_assets_are_served_from_the_site_root(self):
        for url, content_type in (('/favicon.ico', 'image/x-icon'), ('/icon.svg', 'image/svg+xml'),
                                  ('/apple-icon.png', 'image/png'), ('/og-default.png', 'image/png')):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertEqual(response['Content-Type'], content_type, url)
            self.assertTrue(b''.join(response.streaming_content))

    def test_only_existing_top_level_assets_are_served(self):
        self.assertEqual(self.client.get('/missing.png').status_code, 404)
        self.assertEqual(self.client.get('/secret.html').status_code, 404)    # not an asset type
        self.assertEqual(self.client.get('/admin/og-default.png').status_code, 404)  # not top-level
        self.assertEqual(self.client.get('/..%2Fsecret.png').status_code, 404)

    # ---------------------------------------------------------------- 9/10. sitemap, robots

    def test_sitemap_has_public_pages_only(self):
        body = self.client.get('/sitemap.xml').content.decode()
        for path in ('/', '/search', '/about', '/contact', '/privacy', '/terms', f'/property/{self.approved.id}'):
            self.assertIn(f'<loc>{CANONICAL}{path}</loc>', body)
        self.assertNotIn(str(self.pending.id), body)
        for private in ('/admin', '/owner', '/login', '/register', '/bookings', '/booking/'):
            self.assertNotIn(f'{CANONICAL}{private}', body)

    def test_robots_txt_unchanged_with_canonical_sitemap(self):
        body = self.client.get('/robots.txt').content.decode()
        self.assertIn('Sitemap: https://slbooking.hotel.lk/sitemap.xml', body)
        for line in ('Disallow: /owner/', 'Disallow: /admin/', 'Disallow: /login', 'Disallow: /register', 'Disallow: /bookings'):
            self.assertIn(line, body)

    # ---------------------------------------------------------------- helpers

    def assertSingleSocialTags(self, html):
        for name in ('og:title', 'og:description', 'og:url', 'og:type', 'og:site_name', 'og:image'):
            self.assertEqual(len(tags(html, rf'<meta property="{name}" ')), 1, name)
        for name in ('twitter:card', 'twitter:title', 'twitter:description', 'twitter:image'):
            self.assertEqual(len(tags(html, rf'<meta name="{name}" ')), 1, name)
        self.assertEqual(len(tags(html, r'<link rel="canonical"')), 1)
        self.assertEqual(len(tags(html, r'<title>')), 1)
        self.assertEqual(len(tags(html, r'<meta name="description"')), 1)
