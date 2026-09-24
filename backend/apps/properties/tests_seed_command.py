"""
Tests for the idempotent seed_master_data management command (P0-5/P0-6):
production's Amenity table is empty, and its PropertyType table has a
custom "Entry Villa" record that must never be overwritten by seeding.

Run with: python manage.py test apps.properties.tests_seed_command
"""

from django.core.management import call_command
from django.test import TestCase

from .models import Amenity, PropertyType


class SeedMasterDataCommandTestCase(TestCase):
    def test_seeds_amenities_into_empty_table(self):
        """Simulates production: Amenity table starts completely empty."""
        self.assertEqual(Amenity.objects.count(), 0)

        call_command('seed_master_data')

        self.assertGreater(Amenity.objects.count(), 0)
        self.assertTrue(Amenity.objects.filter(slug='wifi').exists())
        self.assertTrue(Amenity.objects.filter(slug='swimming-pool').exists())

    def test_does_not_duplicate_amenities_on_second_run(self):
        call_command('seed_master_data')
        first_count = Amenity.objects.count()

        call_command('seed_master_data')
        second_count = Amenity.objects.count()

        self.assertEqual(first_count, second_count)

    def test_preserves_existing_custom_property_type(self):
        """
        Simulates production: a hand-added "Entry Villa" PropertyType (pk=1)
        that differs from the local fixture's "Villa" must survive seeding
        untouched - never overwritten, never renamed, never duplicated away.
        """
        custom_type = PropertyType.objects.create(name='Entry Villa', description='Full Villa')

        call_command('seed_master_data')

        custom_type.refresh_from_db()
        self.assertEqual(custom_type.name, 'Entry Villa')
        self.assertEqual(custom_type.description, 'Full Villa')
        # The default "Villa" is a distinct row added alongside it, not a
        # replacement for the custom one.
        self.assertTrue(PropertyType.objects.filter(name='Villa').exists())
        self.assertTrue(PropertyType.objects.filter(name='Entry Villa').exists())

    def test_does_not_duplicate_property_types_on_second_run(self):
        call_command('seed_master_data')
        first_count = PropertyType.objects.count()

        call_command('seed_master_data')
        second_count = PropertyType.objects.count()

        self.assertEqual(first_count, second_count)

    def test_existing_amenity_with_same_slug_is_not_duplicated_or_altered(self):
        """An amenity already seeded under a slug keeps its own data (e.g. a
        custom icon_url an admin set) rather than being reset to defaults."""
        existing = Amenity.objects.create(name='WiFi (Custom)', slug='wifi', icon_url='https://example.com/wifi.png')

        call_command('seed_master_data')

        existing.refresh_from_db()
        self.assertEqual(existing.name, 'WiFi (Custom)')
        self.assertEqual(existing.icon_url, 'https://example.com/wifi.png')
        self.assertEqual(Amenity.objects.filter(slug='wifi').count(), 1)
