"""
Tests for the idempotent seed_master_data management command.

Master data identity is the amenity slug/name and the property type name -
never a numeric id. Existing records are never deleted, renamed or
(de)activated; production's hand-added "Entry Villa" type must survive.

Run with: python manage.py test apps.properties.tests_seed_command
"""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .management.commands.seed_master_data import (
    LEGACY_DEFAULT_CATEGORIES, MASTER_AMENITIES, master_amenity_entries,
)
from .models import Amenity, Property, PropertyAmenity, PropertyType

MASTER_COUNT = sum(len(names) for names in MASTER_AMENITIES.values())

# The standard room-based types defined by the project (fixtures/property_types.json)
ROOM_BASED_TYPES = ['Villa', 'Hotel', 'Guest House', 'Apartment', 'Holiday Home', 'Resort', 'Bungalow', 'Homestay']

# The 25 amenities an earlier version of this command seeded (name, slug)
LEGACY_SEED = [
    ('WiFi', 'wifi'), ('Swimming Pool', 'swimming-pool'), ('Parking', 'parking'),
    ('Air Conditioning', 'air-conditioning'), ('Kitchen', 'kitchen'), ('Restaurant', 'restaurant'),
    ('Breakfast Included', 'breakfast-included'), ('Garden', 'garden'), ('Beach Access', 'beach-access'),
    ('Hot Water', 'hot-water'), ('TV', 'tv'), ('Washing Machine', 'washing-machine'),
    ('Airport Transfer', 'airport-transfer'), ('BBQ', 'bbq'), ('Private Pool', 'private-pool'),
    ('Balcony', 'balcony'), ('Sea View', 'sea-view'), ('Mountain View', 'mountain-view'),
    ('Room Service', 'room-service'), ('Bar', 'bar'), ('Gym / Fitness Center', 'gym-fitness-center'),
    ('Spa', 'spa'), ('Pet Friendly', 'pet-friendly'), ('Elevator', 'elevator'),
    ('24-Hour Front Desk', '24-hour-front-desk'),
]


def seed(*args):
    out = StringIO()
    call_command('seed_master_data', *args, stdout=out)
    return out.getvalue()


class SeedMasterDataCommandTestCase(TestCase):

    def test_master_list_is_complete_and_unique(self):
        entries = master_amenity_entries()
        self.assertEqual(MASTER_COUNT, 60)
        self.assertEqual(len({e['slug'] for e in entries}), 60)
        self.assertEqual(len({e['name'].lower() for e in entries}), 60)

    def test_seeds_all_master_amenities_into_empty_table(self):
        """Production's Amenity table started completely empty."""
        self.assertEqual(Amenity.objects.count(), 0)
        output = seed()
        self.assertIn(f'{MASTER_COUNT} created, 0 already existing, 0 skipped', output)
        self.assertEqual(Amenity.objects.count(), MASTER_COUNT)
        for category, names in MASTER_AMENITIES.items():
            for name in names:
                amenity = Amenity.objects.get(name=name)
                self.assertEqual(amenity.category, category)
                self.assertTrue(amenity.is_active)
        self.assertEqual(Amenity.objects.get(name="Children's Playground").slug, 'childrens-playground')

    def test_running_twice_creates_no_duplicates(self):
        seed()
        ids = sorted(Amenity.objects.values_list('id', flat=True))
        output = seed()
        self.assertIn(f'0 created, {MASTER_COUNT} already existing, 0 skipped', output)
        self.assertEqual(sorted(Amenity.objects.values_list('id', flat=True)), ids)

    def test_existing_legacy_amenities_are_preserved_and_topped_up(self):
        """Production after the previous seed: the 25 older defaults already exist."""
        for name, slug in LEGACY_SEED:
            Amenity.objects.create(name=name, slug=slug, category=LEGACY_DEFAULT_CATEGORIES[slug])
        legacy_ids = {slug: Amenity.objects.get(slug=slug).id for _, slug in LEGACY_SEED}

        output = seed()

        self.assertIn('44 created, 16 already existing, 0 skipped', output)
        self.assertEqual(Amenity.objects.count(), 25 + 44)
        # Nothing deleted, renamed or re-keyed
        for name, slug in LEGACY_SEED:
            amenity = Amenity.objects.get(slug=slug)
            self.assertEqual(amenity.id, legacy_ids[slug])
            self.assertEqual(amenity.name, name)
        # Synonyms reuse the existing row instead of creating near-duplicates
        for new_slug in ('gym-fitness-centre', 'bbq-barbecue-facilities', 'pets-allowed', 'airport-shuttle'):
            self.assertFalse(Amenity.objects.filter(slug=new_slug).exists(), new_slug)
        # Untouched legacy categories move into the master grouping...
        self.assertEqual(Amenity.objects.get(slug='wifi').category, 'Property Basics')
        self.assertEqual(Amenity.objects.get(slug='gym-fitness-center').category, 'Wellness')
        # ...while amenities outside the master list keep theirs
        self.assertEqual(Amenity.objects.get(slug='restaurant').category, 'dining')

    def test_customised_category_is_never_overwritten(self):
        Amenity.objects.create(name='WiFi', slug='wifi', category='Connectivity (custom)')
        seed()
        self.assertEqual(Amenity.objects.get(slug='wifi').category, 'Connectivity (custom)')

    def test_existing_amenity_with_same_slug_is_not_duplicated_or_altered(self):
        """An amenity already seeded under a slug keeps its own data (e.g. a
        custom icon_url an admin set) rather than being reset to defaults."""
        existing = Amenity.objects.create(name='WiFi (Custom)', slug='wifi', icon_url='https://example.com/wifi.png')
        seed()
        existing.refresh_from_db()
        self.assertEqual(existing.name, 'WiFi (Custom)')
        self.assertEqual(existing.icon_url, 'https://example.com/wifi.png')
        self.assertEqual(Amenity.objects.filter(slug='wifi').count(), 1)

    def test_existing_amenity_matched_by_name_is_not_duplicated(self):
        Amenity.objects.create(name='hair dryer', slug='hairdryer-custom')
        seed()
        self.assertEqual(Amenity.objects.filter(name__iexact='hair dryer').count(), 1)
        self.assertFalse(Amenity.objects.filter(slug='hair-dryer').exists())

    def test_inactive_amenity_stays_inactive(self):
        Amenity.objects.create(name='Spa', slug='spa', is_active=False)
        output = seed()
        self.assertFalse(Amenity.objects.get(slug='spa').is_active)
        self.assertIn('1 existing inactive left inactive', output)

    def test_conflicting_slug_and_name_are_skipped_not_guessed(self):
        Amenity.objects.create(name='Toaster Oven Combo', slug='toaster')
        Amenity.objects.create(name='Toaster', slug='bread-toaster')
        output = seed()
        self.assertIn('1 skipped', output)
        self.assertEqual(Amenity.objects.filter(slug='toaster').get().name, 'Toaster Oven Combo')

    def test_dry_run_changes_nothing(self):
        output = seed('--dry-run')
        self.assertIn(f'{MASTER_COUNT} created', output)
        self.assertIn('DRY RUN', output)
        self.assertEqual(Amenity.objects.count(), 0)

    def test_property_types_and_entry_villa_untouched(self):
        """A hand-added "Entry Villa" (pk=1 in production) is never altered."""
        custom_type = PropertyType.objects.create(name='Entry Villa', description='Full Villa',
                                                  booking_mode='whole_property')
        seed()
        custom_type.refresh_from_db()
        self.assertEqual(custom_type.name, 'Entry Villa')
        self.assertEqual(custom_type.description, 'Full Villa')
        self.assertEqual(custom_type.booking_mode, 'whole_property')
        self.assertTrue(PropertyType.objects.filter(name='Villa').exists())

    def test_does_not_duplicate_property_types_on_second_run(self):
        seed()
        first_count = PropertyType.objects.count()
        seed()
        self.assertEqual(PropertyType.objects.count(), first_count)

    # ---- Property types --------------------------------------------------

    def test_seeds_all_standard_property_types(self):
        output = seed()
        self.assertIn('Property types: 9 created, 0 already existing, 0 skipped', output)
        for name in ROOM_BASED_TYPES:
            ptype = PropertyType.objects.get(name=name)
            self.assertEqual(ptype.booking_mode, 'room_types', name)
            self.assertTrue(ptype.is_active)
        entry_villa = PropertyType.objects.get(name='Entry Villa')
        self.assertEqual(entry_villa.booking_mode, 'whole_property')
        self.assertTrue(entry_villa.is_active)

    def test_production_restore_keeps_existing_entry_villa(self):
        """Production today: ONLY the hand-added Entry Villa (whole_property) exists."""
        entry_villa = PropertyType.objects.create(name='Entry Villa', description='Full Villa',
                                                  booking_mode='whole_property', is_active=True)
        before = PropertyType.objects.filter(pk=entry_villa.pk).values().get()

        output = seed()

        self.assertIn('Property types: 8 created, 1 already existing, 0 skipped', output)
        self.assertEqual(PropertyType.objects.filter(pk=entry_villa.pk).values().get(), before)  # every field unchanged
        self.assertEqual(PropertyType.objects.filter(name__iexact='entry villa').count(), 1)
        self.assertEqual(
            set(PropertyType.objects.exclude(pk=entry_villa.pk).values_list('booking_mode', flat=True)),
            {'room_types'},
        )
        self.assertEqual(PropertyType.objects.count(), 9)

    def test_property_types_not_duplicated_when_run_twice(self):
        seed()
        ids = sorted(PropertyType.objects.values_list('id', flat=True))
        output = seed()
        self.assertIn('Property types: 0 created, 9 already existing, 0 skipped', output)
        self.assertEqual(sorted(PropertyType.objects.values_list('id', flat=True)), ids)

    def test_property_type_name_match_is_case_insensitive(self):
        PropertyType.objects.create(name='hotel')
        seed()
        self.assertEqual(PropertyType.objects.filter(name__iexact='hotel').count(), 1)
        self.assertTrue(PropertyType.objects.filter(name='hotel').exists())  # original name kept

    def test_existing_types_are_never_modified_or_reactivated(self):
        inactive = PropertyType.objects.create(name='Bungalow', is_active=False)
        custom_mode = PropertyType.objects.create(name='Villa', booking_mode='whole_property')
        output = seed()
        inactive.refresh_from_db()
        custom_mode.refresh_from_db()
        self.assertFalse(inactive.is_active)
        self.assertEqual(custom_mode.booking_mode, 'whole_property')
        self.assertIn("Property type 'Villa' has booking_mode 'whole_property'", output)

    def test_existing_properties_are_not_modified(self):
        from django.contrib.auth import get_user_model
        owner = get_user_model().objects.create_user(email='seed-prop-owner@example.com', password='test')
        entry_villa = PropertyType.objects.create(name='Entry Villa', booking_mode='whole_property')
        prop = Property.objects.create(owner=owner, property_type=entry_villa, name='Tea House Villa',
                                       description='d', city='Ella', district='Badulla', province='Uva',
                                       status='approved')
        before = Property.objects.filter(pk=prop.pk).values().get()
        seed()
        self.assertEqual(Property.objects.filter(pk=prop.pk).values().get(), before)

    def test_existing_property_amenity_links_are_untouched(self):
        from django.contrib.auth import get_user_model
        owner = get_user_model().objects.create_user(email='seed-owner@example.com', password='test')
        wifi = Amenity.objects.create(name='WiFi', slug='wifi', category='connectivity')
        prop = Property.objects.create(owner=owner, name='Seed Villa', description='d', city='Galle',
                                       district='Galle', province='Southern')
        PropertyAmenity.objects.create(property=prop, amenity=wifi)
        seed()
        self.assertEqual(list(prop.amenities.values_list('id', flat=True)), [wifi.id])
