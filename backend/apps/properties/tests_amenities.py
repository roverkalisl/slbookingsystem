"""
Amenity master data: API, property creation with real ids, and a guard that
the frontend never hardcodes amenity ids.

Run with: python manage.py test apps.properties.tests_amenities
"""

import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from io import StringIO
from rest_framework.test import APITestCase

from apps.core.models import Role, UserRole
from .models import Amenity, Property, PropertyType

User = get_user_model()
FRONTEND_SRC = Path(settings.BASE_DIR).parent / 'frontend' / 'src'


class AmenityApiTestCase(APITestCase):
    def setUp(self):
        call_command('seed_master_data', stdout=StringIO())
        Amenity.objects.create(name='Retired Amenity', slug='retired-amenity', is_active=False)

    def test_api_returns_all_active_amenities_unpaginated(self):
        response = self.client.get('/api/properties/amenities/')
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertIsInstance(data, list)  # not paginated - every amenity in one response
        self.assertEqual(len(data), Amenity.objects.filter(is_active=True).count())
        self.assertGreaterEqual(len(data), 60)
        first = data[0]
        for key in ('id', 'name', 'slug', 'category'):
            self.assertIn(key, first)
        names = {a['name'] for a in data}
        self.assertIn('Baby Cot / Crib', names)
        self.assertNotIn('Retired Amenity', names)

    def test_api_ids_are_the_database_ids(self):
        data = self.client.get('/api/properties/amenities/').data
        for item in data:
            self.assertEqual(Amenity.objects.get(slug=item['slug']).id, item['id'])


class PropertyAmenityIdsTestCase(APITestCase):
    def setUp(self):
        call_command('seed_master_data', stdout=StringIO())
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='amenity-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.client.force_authenticate(self.owner)
        self.property_type = PropertyType.objects.get(name='Hotel')

    def payload(self, amenity_ids):
        return {
            'name': 'Amenity Test Hotel', 'property_type': self.property_type.id, 'description': 'desc',
            'city': 'Kandy', 'district': 'Kandy', 'province': 'Central', 'status': 'draft',
            'amenity_ids': amenity_ids,
        }

    def test_property_creation_accepts_real_amenity_ids_from_api(self):
        api_amenities = self.client.get('/api/properties/amenities/').data
        chosen = [a['id'] for a in api_amenities if a['name'] in ('WiFi', 'Private Pool', 'CCTV')]
        self.assertEqual(len(chosen), 3)
        response = self.client.post('/api/properties/', self.payload(chosen), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        prop = Property.objects.get(name='Amenity Test Hotel')
        self.assertEqual(sorted(prop.amenities.values_list('id', flat=True)), sorted(chosen))

    def test_invalid_amenity_id_is_rejected(self):
        missing_id = (Amenity.objects.order_by('-id').first().id or 0) + 1000
        response = self.client.post('/api/properties/', self.payload([missing_id]), format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('amenity_ids', response.data)
        self.assertFalse(Property.objects.filter(name='Amenity Test Hotel').exists())

    def test_non_numeric_amenity_id_is_rejected(self):
        response = self.client.post('/api/properties/', self.payload(['wifi']), format='json')
        self.assertEqual(response.status_code, 400)


class FrontendAmenityIdsTestCase(APITestCase):
    """
    Static guard (no JS test runner in this project): the property wizard must
    load amenities from GET /api/properties/amenities/ and submit the returned
    database ids - never array indexes or hardcoded ids.
    """

    def read(self, relative):
        path = FRONTEND_SRC / relative
        if not path.exists():
            self.skipTest(f'frontend source not present: {path}')
        return path.read_text(encoding='utf-8')

    def test_api_client_loads_amenities_from_backend(self):
        source = self.read('lib/api.ts')
        self.assertIn("'/properties/amenities/'", source)

    def test_add_property_uses_api_ids(self):
        source = self.read('app/owner/properties/add/page.tsx')
        self.assertIn('api.getAmenities()', source)
        self.assertIn('amenity_ids: selectedAmenities', source)
        self.assertIn('selectedAmenities.includes(amenity.id)', source)
        # No index-derived or hardcoded amenity ids
        self.assertIsNone(re.search(r'(index|idx|i)\s*\+\s*1', source))
        self.assertIsNone(re.search(r'amenity_ids\s*:\s*\[\s*\d', source))

    def test_no_hardcoded_amenity_ids_anywhere_in_frontend(self):
        if not FRONTEND_SRC.exists():
            self.skipTest('frontend source not present')
        offenders = []
        for path in FRONTEND_SRC.rglob('*.ts*'):
            text = path.read_text(encoding='utf-8', errors='ignore')
            if re.search(r'amenity_ids\s*[:=]\s*\[\s*\d', text):
                offenders.append(str(path))
        self.assertEqual(offenders, [])
