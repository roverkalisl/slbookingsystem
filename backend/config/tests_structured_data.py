"""
Property structured data (Schema.org LodgingBusiness JSON-LD) on approved
public property pages - config/seo.py property_json_ld / inject_property_seo.

Run with: python manage.py test config.tests_structured_data
"""

import json
import os
import re
import tempfile
from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from apps.bookings.models import Booking
from apps.properties.models import (Amenity, Pricing, Property, PropertyAmenity, PropertyContact,
                                    PropertyPhoto, PropertyType, RoomType)
from apps.reviews.models import Review
from config.seo import json_ld_script, property_json_ld
from config.urls import serve_frontend

User = get_user_model()
CANONICAL = 'https://slbooking.hotel.lk'
SHELL = ('<!DOCTYPE html><html lang="en"><head><meta charSet="utf-8"/>'
         '<title>SL Booking - Sri Lankan Accommodation Marketplace</title>'
         '<meta name="description" content="Book accommodations across Sri Lanka"/></head>'
         '<body>property shell</body></html>')
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def walk(value):
    """Every nested value of a JSON document."""
    if isinstance(value, dict):
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)
    else:
        yield value


@override_settings(CANONICAL_SITE_URL=CANONICAL)
class PropertyStructuredDataTestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.makedirs(os.path.join(self.tmp.name, 'property'))
        for name, content in (('property/0.html', SHELL), ('index.html', '<html><head></head><body>home</body></html>'),
                              ('404.html', 'nf'), ('login.html', SHELL)):
            with open(os.path.join(self.tmp.name, name), 'w', encoding='utf-8') as f:
                f.write(content)
        self.static = override_settings(STATIC_ROOT=self.tmp.name)
        self.static.enable()

        self.owner = User.objects.create_user(email='ld-owner@example.com', password='x', phone='0771112222',
                                              first_name='Olivia', last_name='Owner')
        self.guest = User.objects.create_user(email='ld-guest@example.com', password='x', first_name='Gary', last_name='Guest')
        self.hotel = PropertyType.objects.create(name='LD Villa')
        self.prop = Property.objects.create(
            owner=self.owner, property_type=self.hotel, name='Lake View Villa', status='approved',
            short_description='Quiet lakeside villa', description='A quiet villa beside Kandy Lake with a garden and pool.',
            address='12 Secret Lane', postal_code='20000', latitude=Decimal('7.29060000'), longitude=Decimal('80.63370000'),
            city='Kandy', district='Kandy', province='Central',
        )
        PropertyContact.objects.create(property=self.prop, contact_phone='0812223344', whatsapp_number='0779998888',
                                       email='private-contact@example.com')
        PropertyPhoto.objects.create(property=self.prop, cloudinary_url='https://res.cloudinary.com/demo/second.jpg',
                                     cloudinary_public_id='second', display_order=0)
        PropertyPhoto.objects.create(property=self.prop, cloudinary_url='https://res.cloudinary.com/demo/cover.jpg',
                                     cloudinary_public_id='cover', display_order=5, is_cover=True)
        for bad in ('http://res.cloudinary.com/demo/insecure.jpg', 'https://localhost/x.jpg',
                    'https://slbookingsystem.onrender.com/static/x.jpg'):
            PropertyPhoto.objects.create(property=self.prop, cloudinary_url=bad, cloudinary_public_id=bad[-10:], display_order=9)
        pool = Amenity.objects.create(name='Swimming Pool', slug='ld-pool')
        wifi = Amenity.objects.create(name='WiFi', slug='ld-wifi')
        retired = Amenity.objects.create(name='Retired Thing', slug='ld-retired', is_active=False)
        for amenity in (pool, wifi, retired):
            PropertyAmenity.objects.create(property=self.prop, amenity=amenity)
        for name, price in (('Double', '15000.00'), ('Suite', '25000.00')):
            room = RoomType.objects.create(property=self.prop, name=name, max_adults=2, total_occupancy=2, total_rooms=1)
            Pricing.objects.create(room_type=room, base_price=Decimal(price))

    def tearDown(self):
        self.static.disable()
        self.tmp.cleanup()

    def page(self, prop):
        return serve_frontend(RequestFactory().get(f'/property/{prop.id}'), path=f'property/{prop.id}').content.decode()

    def json_ld_blocks(self, html):
        return [json.loads(block) for block in LD_RE.findall(html)]

    # --- presence ---

    def test_approved_property_has_exactly_one_lodging_business_block_in_head(self):
        html = self.page(self.prop)
        blocks = self.json_ld_blocks(html)
        self.assertEqual(len(blocks), 1)
        self.assertLess(html.index('application/ld+json'), html.index('</head>'))
        data = blocks[0]
        self.assertEqual(data['@context'], 'https://schema.org')
        self.assertEqual(data['@type'], 'LodgingBusiness')
        self.assertEqual(data['name'], 'Lake View Villa')
        self.assertEqual(data['url'], f'{CANONICAL}/property/{self.prop.id}')
        self.assertEqual(data['@id'], f'{CANONICAL}/property/{self.prop.id}#lodging')
        self.assertEqual(data['description'], 'A quiet villa beside Kandy Lake with a garden and pool.')

    def test_unapproved_properties_have_no_json_ld(self):
        for status in ('draft', 'pending_approval', 'rejected', 'suspended', 'unpublished'):
            Property.objects.filter(pk=self.prop.pk).update(status=status)
            html = self.page(self.prop)
            self.assertNotIn('application/ld+json', html, status)
            self.assertNotIn('Lake View Villa', html, status)

    def test_other_pages_have_no_property_json_ld(self):
        for path in ('', 'login', 'no-such-page', 'property/0', 'property/not-a-uuid'):
            html = serve_frontend(RequestFactory().get(f'/{path}'), path=path).content.decode()
            self.assertNotIn('application/ld+json', html, path)

    # --- values come from real data ---

    def test_real_public_images_cover_first(self):
        data = property_json_ld(self.prop)
        self.assertEqual(data['image'], ['https://res.cloudinary.com/demo/cover.jpg', 'https://res.cloudinary.com/demo/second.jpg'])

    def test_address_has_only_the_publicly_shown_location(self):
        data = property_json_ld(self.prop)
        self.assertEqual(data['address'], {
            '@type': 'PostalAddress', 'addressLocality': 'Kandy', 'addressRegion': 'Central', 'addressCountry': 'LK',
        })
        self.assertNotIn('geo', data)
        serialized = json.dumps(data)
        for private in ('12 Secret Lane', '20000', '7.2906', '80.6337'):
            self.assertNotIn(private, serialized)

    def test_price_range_from_real_base_prices(self):
        self.assertEqual(property_json_ld(self.prop)['priceRange'], 'LKR 15,000 - LKR 25,000')
        Pricing.objects.filter(room_type__name='Suite').update(base_price=Decimal('15000.00'))
        self.assertEqual(property_json_ld(self.prop)['priceRange'], 'LKR 15,000')

    def test_amenities_from_active_linked_amenities(self):
        names = [a['name'] for a in property_json_ld(self.prop)['amenityFeature']]
        self.assertEqual(names, ['Swimming Pool', 'WiFi'])

    # --- ratings ---

    def test_no_reviews_means_no_rating_even_with_stale_property_fields(self):
        Property.objects.filter(pk=self.prop.pk).update(average_rating=Decimal('5.00'), total_reviews=12)
        self.prop.refresh_from_db()
        data = property_json_ld(self.prop)
        self.assertNotIn('aggregateRating', data)
        self.assertNotIn('review', data)

    def test_aggregate_rating_from_real_published_reviews(self):
        room = self.prop.room_types.first()
        check_in = date.today() - timedelta(days=10)
        for i, (rating, published, flagged) in enumerate(((5, True, False), (4, True, False), (1, False, False), (1, True, True))):
            booking = Booking.objects.create(
                booking_reference=f'LD-{i}', property=self.prop, room_type=room, guest=self.guest,
                check_in_date=check_in, check_out_date=check_in + timedelta(days=1), number_of_nights=1,
                number_of_adults=1, room_price=Decimal('1'), subtotal=Decimal('1'), total_price=Decimal('1'), status='completed')
            Review.objects.create(booking=booking, property=self.prop, guest=self.guest, overall_rating=rating,
                                  comment='Lovely', is_published=published, is_flagged=flagged)
        self.assertEqual(property_json_ld(self.prop)['aggregateRating'], {
            '@type': 'AggregateRating', 'ratingValue': 4.5, 'reviewCount': 2, 'bestRating': 5, 'worstRating': 1,
        })
        self.assertNotIn('Gary', json.dumps(property_json_ld(self.prop)))  # no reviewer names

    # --- privacy / validity ---

    def test_no_owner_contact_or_private_data(self):
        html = self.page(self.prop)
        block = LD_RE.findall(html)[0]
        for private in ('ld-owner@example.com', 'Olivia', 'private-contact@example.com', '0812223344',
                        '0779998888', '94779998888', '0771112222', str(self.owner.id), 'telephone', 'email'):
            self.assertNotIn(private, block)

    def test_minimal_property_has_no_null_or_empty_fields(self):
        bare = Property.objects.create(owner=self.owner, property_type=self.hotel, name='Bare Villa', status='approved',
                                       description='', city='', district='', province='')
        data = property_json_ld(bare)
        self.assertEqual(set(data), {'@context', '@type', '@id', 'name', 'url'})
        for value in walk(data):
            self.assertNotIn(value, (None, '', [], {}))
        self.assertTrue(all(v.startswith('https://') for v in (data['url'], data['@id'])))

    def test_every_url_is_absolute_https(self):
        data = property_json_ld(self.prop)
        urls = [data['url'], data['@id'], *data['image']]
        self.assertTrue(all(u.startswith('https://') for u in urls))
        self.assertFalse(any('localhost' in u or 'onrender.com' in u for u in urls))

    def test_script_payload_cannot_break_out_of_the_script_tag(self):
        Property.objects.filter(pk=self.prop.pk).update(name='Villa </script><script>alert(1)</script> & "Co"')
        self.prop.refresh_from_db()
        html = self.page(self.prop)
        self.assertNotIn('<script>alert(1)', html)
        data = self.json_ld_blocks(html)[0]
        self.assertEqual(data['name'], 'Villa </script><script>alert(1)</script> & "Co"')
        self.assertIn('\\u003c/script\\u003e', json_ld_script({'x': '</script>'}))
