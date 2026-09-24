"""
Property cards (Featured / search / list): the image must come from the
property's real photos (the photo flagged is_cover, else the first photo),
and a property with no priced unit must report min_price = null (the UI then
shows "Price not set" instead of "LKR 0").

Run with: python manage.py test apps.properties.tests_property_cards
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Property, PropertyPhoto, PropertyType, Pricing, RoomType

User = get_user_model()
FEATURED_URL = '/api/properties/search/featured/'


class PropertyCardImageAndPriceTestCase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='card-owner@example.com', password='test')
        self.hotel_type = PropertyType.objects.create(name='Card Hotel Type')

    def make_property(self, name, **extra):
        return Property.objects.create(owner=self.owner, property_type=self.hotel_type, name=name,
                                       description='d', city='Ella', district='Badulla', province='Uva',
                                       status='approved', **extra)

    def card(self, url, name):
        data = self.client.get(url).data
        results = data.get('data', data) if isinstance(data, dict) else data
        if isinstance(results, dict):
            results = results.get('results', [])
        return next(p for p in results if p['name'] == name)

    def test_card_uses_the_cover_photo(self):
        prop = self.make_property('Photo Villa')
        PropertyPhoto.objects.create(property=prop, cloudinary_url='https://res.cloudinary.com/demo/second.jpg',
                                     cloudinary_public_id='second', display_order=1)
        PropertyPhoto.objects.create(property=prop, cloudinary_url='https://res.cloudinary.com/demo/cover.jpg',
                                     cloudinary_public_id='cover', display_order=2, is_cover=True)
        self.assertEqual(self.card(FEATURED_URL, 'Photo Villa')['cover_photo_url'],
                         'https://res.cloudinary.com/demo/cover.jpg')

    def test_card_falls_back_to_first_photo_when_none_marked_cover(self):
        prop = self.make_property('First Photo Villa')
        PropertyPhoto.objects.create(property=prop, cloudinary_url='https://res.cloudinary.com/demo/b.jpg',
                                     cloudinary_public_id='b', display_order=2)
        PropertyPhoto.objects.create(property=prop, cloudinary_url='https://res.cloudinary.com/demo/a.jpg',
                                     cloudinary_public_id='a', display_order=1)
        self.assertEqual(self.card(FEATURED_URL, 'First Photo Villa')['cover_photo_url'],
                         'https://res.cloudinary.com/demo/a.jpg')

    def test_chosen_cover_photo_wins_over_a_stale_stored_url(self):
        # Property.cover_photo_url only mirrors the cover photo; the photo flagged is_cover is authoritative.
        prop = self.make_property('Explicit Cover Villa', cover_photo_url='https://res.cloudinary.com/demo/stale.jpg')
        PropertyPhoto.objects.create(property=prop, cloudinary_url='https://res.cloudinary.com/demo/cover.jpg',
                                     cloudinary_public_id='cover', is_cover=True)
        self.assertEqual(self.card(FEATURED_URL, 'Explicit Cover Villa')['cover_photo_url'],
                         'https://res.cloudinary.com/demo/cover.jpg')

    def test_no_photos_gives_null_not_placeholder(self):
        self.make_property('Bare Villa')
        self.assertIsNone(self.card(FEATURED_URL, 'Bare Villa')['cover_photo_url'])

    def test_unpriced_property_reports_null_price(self):
        self.make_property('Unpriced Villa')
        self.assertIsNone(self.card(FEATURED_URL, 'Unpriced Villa')['min_price'])

    def test_priced_property_reports_its_price(self):
        prop = self.make_property('Priced Villa')
        room = RoomType.objects.create(property=prop, name='Room', max_adults=2, total_occupancy=2, total_rooms=1)
        Pricing.objects.create(room_type=room, base_price=Decimal('38000.00'))
        self.assertEqual(Decimal(self.card(FEATURED_URL, 'Priced Villa')['min_price']), Decimal('38000.00'))

    def test_property_list_endpoint_also_returns_cover(self):
        prop = self.make_property('Listed Villa')
        PropertyPhoto.objects.create(property=prop, cloudinary_url='https://res.cloudinary.com/demo/listed.jpg',
                                     cloudinary_public_id='listed')
        self.assertEqual(self.card('/api/properties/', 'Listed Villa')['cover_photo_url'],
                         'https://res.cloudinary.com/demo/listed.jpg')
        prop.refresh_from_db()
        self.assertIsNone(prop.cover_photo_url)  # read-only fallback - no data written
