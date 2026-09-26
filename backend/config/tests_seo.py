"""
robots.txt, sitemap.xml and property page SEO (config/seo.py + serve_frontend).

Run with: python manage.py test config.tests_seo
"""

import os
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from apps.properties.models import Property, PropertyContact, PropertyPhoto, PropertyType
from config.urls import serve_frontend

User = get_user_model()
CANONICAL = 'https://slbooking.hotel.lk'
SITEMAP_NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'

# Same shape as the real export's <head> (frontend/out/property/0.html)
SHELL = (
    '<!DOCTYPE html><html lang="en"><head><meta charSet="utf-8"/>'
    '<title>SL Booking - Sri Lankan Accommodation Marketplace</title>'
    '<meta name="description" content="Book accommodations across Sri Lanka - Villas, Apartments, Resorts"/>'
    '<meta name="author" content="SL Booking"/></head><body><div id="app">property shell</div></body></html>'
)


class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title, self.meta, self.links, self._in_title = '', {}, {}, False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self._in_title = True
        elif tag == 'meta':
            key = attrs.get('property') or attrs.get('name')
            if key:
                self.meta[key] = attrs.get('content')
        elif tag == 'link' and attrs.get('rel') == 'canonical':
            self.links['canonical'] = attrs.get('href')

    def handle_endtag(self, tag):
        if tag == 'title':
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def head_of(html):
    parser = HeadParser()
    parser.feed(html)
    return parser


@override_settings(CANONICAL_SITE_URL=CANONICAL)
class CrawlerFilesTestCase(TestCase):
    def setUp(self):
        owner = User.objects.create_user(email='seo-owner@example.com', password='x')
        ptype = PropertyType.objects.create(name='SEO Hotel')
        make = lambda name, status: Property.objects.create(owner=owner, property_type=ptype, name=name, description='d',
                                                            city='Galle', district='Galle', province='Southern', status=status)
        self.approved = make('Public Villa', 'approved')
        self.draft = make('Draft Villa', 'draft')
        self.pending = make('Pending Villa', 'pending_approval')
        self.suspended = make('Suspended Villa', 'suspended')

    def test_robots_txt(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('text/plain'))
        body = response.content.decode()
        self.assertIn('User-agent: *', body)
        self.assertIn(f'Sitemap: {CANONICAL}/sitemap.xml', body)
        for private in ('/owner/', '/admin/', '/login', '/bookings'):
            self.assertIn(f'Disallow: {private}', body)
        # The property page loads its content from the API - crawlers must be allowed to fetch it
        self.assertNotIn('Disallow: /api', body)
        self.assertNotIn('<html', body.lower())

    def test_sitemap_is_valid_xml_with_only_public_urls(self):
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response['Content-Type'].startswith('application/xml'))
        root = ET.fromstring(response.content)
        self.assertEqual(root.tag, f'{SITEMAP_NS}urlset')
        locs = [el.text for el in root.iter(f'{SITEMAP_NS}loc')]
        self.assertIn(f'{CANONICAL}/', locs)
        self.assertIn(f'{CANONICAL}/search', locs)
        self.assertIn(f'{CANONICAL}/property/{self.approved.id}', locs)
        for hidden in (self.draft, self.pending, self.suspended):
            self.assertNotIn(f'{CANONICAL}/property/{hidden.id}', locs)
        self.assertTrue(all(loc.startswith(CANONICAL) for loc in locs))
        for private in ('/owner', '/admin', '/login', '/register', '/bookings'):
            self.assertFalse(any(private in loc for loc in locs), private)


@override_settings(CANONICAL_SITE_URL=CANONICAL)
class PropertyPageSeoTestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, 'property'))
        for name, content in (('property/0.html', SHELL), ('index.html', 'home'), ('404.html', 'not found page')):
            with open(os.path.join(self.tmp.name, name), 'w', encoding='utf-8') as f:
                f.write(content)
        self.static = override_settings(STATIC_ROOT=self.tmp.name)
        self.static.enable()

        owner = User.objects.create_user(email='seo-page-owner@example.com', password='x', phone='0771112222')
        ptype = PropertyType.objects.create(name='SEO Page Hotel')
        self.prop = Property.objects.create(
            owner=owner, property_type=ptype, name='Lake View Villa', city='Kandy', district='Kandy',
            province='Central', status='approved', short_description='',
            description='A quiet villa beside Kandy Lake with a garden, pool and views of the hills. ' * 4,
        )
        PropertyContact.objects.create(property=self.prop, whatsapp_number='0779998888', email='secret-owner@example.com')
        PropertyPhoto.objects.create(property=self.prop, cloudinary_url='https://res.cloudinary.com/demo/lake.jpg',
                                     cloudinary_public_id='lake', is_cover=True)
        self.draft = Property.objects.create(owner=owner, property_type=ptype, name='Secret Draft Villa',
                                             description='Private draft text', city='Ella', district='Badulla',
                                             province='Uva', status='draft')

    def tearDown(self):
        self.static.disable()
        self.tmp.cleanup()

    def serve(self, path):
        return serve_frontend(RequestFactory().get(f'/{path}'), path=path)

    def test_approved_property_gets_its_own_metadata(self):
        response = self.serve(f'property/{self.prop.id}')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        head = head_of(html)
        url = f'{CANONICAL}/property/{self.prop.id}'
        self.assertEqual(head.title, 'Lake View Villa - Kandy | SL Booking')
        self.assertTrue(head.meta['description'].startswith('A quiet villa beside Kandy Lake'))
        self.assertLessEqual(len(head.meta['description']), 160)
        self.assertEqual(head.links['canonical'], url)
        self.assertEqual(head.meta['og:title'], 'Lake View Villa - Kandy | SL Booking')
        self.assertEqual(head.meta['og:description'], head.meta['description'])
        self.assertEqual(head.meta['og:url'], url)
        self.assertEqual(head.meta['og:type'], 'website')
        self.assertEqual(head.meta['og:image'], 'https://res.cloudinary.com/demo/lake.jpg')
        self.assertEqual(head.meta['twitter:card'], 'summary_large_image')
        self.assertEqual(html.count('<title>'), 1)
        self.assertEqual(html.count('name="description"'), 1)
        self.assertIn('property shell', html)  # the page body is untouched

    def test_no_private_contact_details_in_metadata(self):
        html = self.serve(f'property/{self.prop.id}').content.decode()
        for private in ('secret-owner@example.com', '0779998888', '94779998888', '0771112222', 'seo-page-owner'):
            self.assertNotIn(private, html)

    def test_property_without_photo_has_no_og_image(self):
        PropertyPhoto.objects.filter(property=self.prop).delete()
        head = head_of(self.serve(f'property/{self.prop.id}').content.decode())
        self.assertNotIn('og:image', head.meta)
        self.assertEqual(head.meta['twitter:card'], 'summary')

    def test_unapproved_property_is_not_exposed(self):
        for status in ('draft', 'pending_approval', 'rejected', 'suspended', 'unpublished'):
            Property.objects.filter(pk=self.draft.pk).update(status=status)
            html = self.serve(f'property/{self.draft.id}').content.decode()
            head = head_of(html)
            self.assertEqual(head.title, 'SL Booking - Sri Lankan Accommodation Marketplace', status)
            self.assertNotIn('Secret Draft Villa', html)
            self.assertNotIn('Private draft text', html)
            self.assertNotIn('canonical', head.links)

    def test_missing_or_malformed_property_serves_generic_shell(self):
        for path in ('property/3f2c7a9e-1b2d-4c5e-8f90-123456789abc', 'property/not-a-uuid', 'property/0'):
            response = self.serve(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertEqual(head_of(response.content.decode()).title, 'SL Booking - Sri Lankan Accommodation Marketplace')

    def test_metadata_is_html_escaped(self):
        Property.objects.filter(pk=self.prop.pk).update(name='Villa "Sun" <script>alert(1)</script>',
                                                        short_description='Pool & garden "view"')
        html = self.serve(f'property/{self.prop.id}').content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('Villa &quot;Sun&quot; &lt;script&gt;', html)
        self.assertEqual(head_of(html).meta['description'], 'Pool & garden "view"')

    def test_unknown_paths_get_404_not_the_home_page(self):
        # (/ads.txt is now its own Django route - see config/tests_adsense.py)
        for path in ('no-such-file.txt', 'no-such-page', 'property/abc/extra'):
            response = self.serve(path)
            self.assertEqual(response.status_code, 404, path)
            self.assertEqual(response.content.decode(), 'not found page')
