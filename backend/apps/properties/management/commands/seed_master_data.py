"""
Idempotent seed for master data (Amenity, PropertyType) that the frontend
depends on being non-empty (e.g. GET /api/properties/amenities/).

Unlike `loaddata`, which keys on numeric primary keys and would either
collide with or silently overwrite whatever already has those same IDs in
production, this command matches on stable logical identity - Amenity.slug /
name and PropertyType.name - and only ever creates rows that are missing.
Anything already in the database (including hand-added/customised records
like a production "Entry Villa" PropertyType) is left untouched: nothing is
ever deleted, renamed, deactivated or re-activated.

The one change it makes to existing amenities: an amenity whose category is
still the value an EARLIER version of this command gave it (i.e. nobody has
customised it) is moved into the current master-list category, so the
amenity picker groups consistently. A category an admin changed is never
overwritten.

Safe to run repeatedly and safe to run against a database that already has
data: run again after adding a new default here to top up only what's new.

Run with:  python manage.py seed_master_data
Production: python manage.py seed_master_data --settings=config.settings.production
(Render runs it automatically after migrations - see render.yaml preDeployCommand.)
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.properties.models import Amenity, PropertyType


# Master amenity list: category -> amenity names. Identity is the slug
# (slugify(name)), never a numeric id.
MASTER_AMENITIES = {
    'Property Basics': [
        'WiFi', 'Free Parking', 'Air Conditioning', 'Fan', 'Heating', 'Hot Water', 'TV',
        'Cable / Satellite TV',
    ],
    'Kitchen & Dining': [
        'Kitchen', 'Refrigerator', 'Microwave', 'Oven', 'Stove', 'Electric Kettle', 'Toaster',
        'Dining Area', 'Dining Table', 'BBQ / Barbecue Facilities',
    ],
    'Bathroom': [
        'Private Bathroom', 'Shared Bathroom', 'Shower', 'Bathtub', 'Hair Dryer', 'Toiletries',
    ],
    'Outdoor': [
        'Swimming Pool', 'Private Pool', 'Garden', 'Terrace', 'Balcony', 'Outdoor Dining Area',
        'Outdoor Furniture', 'BBQ Area',
    ],
    'Family': [
        'Family Friendly', "Children's Playground", 'Baby Cot / Crib', 'High Chair',
    ],
    'Services': [
        'Airport Shuttle', 'Room Service', 'Laundry Service', 'Daily Housekeeping',
        'Luggage Storage', 'Tour / Excursion Assistance',
    ],
    'Security': [
        'CCTV', '24-Hour Security', 'Safety Deposit Box', 'Fire Extinguisher', 'Smoke Alarm',
    ],
    'Wellness': [
        'Yoga Area', 'Spa', 'Massage', 'Gym / Fitness Centre',
    ],
    'Activities': [
        'Beach Access', 'Cycling', 'Hiking', 'Fishing', 'Water Sports',
    ],
    'Accessibility': [
        'Ground Floor Access', 'Wheelchair Accessible', 'Accessible Parking',
    ],
    'Pet Policy': [
        'Pets Allowed',
    ],
}

# Master entries that are exact synonyms of an amenity an earlier version of
# this command seeded under a different slug. They reuse that existing row
# instead of creating a near-duplicate (e.g. "Centre" vs "Center").
LEGACY_ALIASES = {
    'gym-fitness-centre': 'gym-fitness-center',        # "Gym / Fitness Center"
    'bbq-barbecue-facilities': 'bbq',                  # "BBQ"
    'pets-allowed': 'pet-friendly',                    # "Pet Friendly"
    'airport-shuttle': 'airport-transfer',             # "Airport Transfer"
}

# Categories the previous version of this command assigned, by slug. Used only
# to recognise "category never customised" before regrouping an existing row.
LEGACY_DEFAULT_CATEGORIES = {
    'wifi': 'connectivity', 'swimming-pool': 'recreation', 'parking': 'general',
    'air-conditioning': 'room', 'kitchen': 'general', 'restaurant': 'dining',
    'breakfast-included': 'dining', 'garden': 'recreation', 'beach-access': 'recreation',
    'hot-water': 'room', 'tv': 'room', 'washing-machine': 'general',
    'airport-transfer': 'services', 'bbq': 'recreation', 'private-pool': 'recreation',
    'balcony': 'room', 'sea-view': 'room', 'mountain-view': 'room', 'room-service': 'services',
    'bar': 'dining', 'gym-fitness-center': 'recreation', 'spa': 'recreation',
    'pet-friendly': 'general', 'elevator': 'general', '24-hour-front-desk': 'services',
}

ROOM_TYPES = PropertyType.BOOKING_MODE_ROOM_TYPES
WHOLE_PROPERTY = PropertyType.BOOKING_MODE_WHOLE_PROPERTY

# Standard property types (same set as fixtures/property_types.json), identified
# by NAME - PropertyType has no slug/code field and numeric ids differ per
# environment. Room-based types book through owner-managed room types; Entry
# Villa is booked as a whole (see migration 0006). Existing rows - including a
# production "Entry Villa" - are never modified.
DEFAULT_PROPERTY_TYPES = [
    {'name': 'Villa', 'description': None, 'booking_mode': ROOM_TYPES},
    {'name': 'Hotel', 'description': None, 'booking_mode': ROOM_TYPES},
    {'name': 'Guest House', 'description': None, 'booking_mode': ROOM_TYPES},
    {'name': 'Apartment', 'description': None, 'booking_mode': ROOM_TYPES},
    {'name': 'Holiday Home', 'description': None, 'booking_mode': ROOM_TYPES},
    {'name': 'Resort', 'description': None, 'booking_mode': ROOM_TYPES},
    {'name': 'Bungalow', 'description': None, 'booking_mode': ROOM_TYPES},
    {'name': 'Homestay', 'description': None, 'booking_mode': ROOM_TYPES},
    {'name': 'Entry Villa', 'description': 'Full Villa', 'booking_mode': WHOLE_PROPERTY},
]


def master_amenity_entries():
    """Flatten MASTER_AMENITIES into [{'name', 'slug', 'category'}] in a stable order."""
    return [
        {'name': name, 'slug': slugify(name), 'category': category}
        for category, names in MASTER_AMENITIES.items()
        for name in names
    ]


class Command(BaseCommand):
    help = 'Idempotently seed master Amenity and PropertyType records without touching existing data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would be created/regrouped, then roll back (no changes saved).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        created = existing = skipped = regrouped = inactive = 0

        for entry in master_amenity_entries():
            by_slug = Amenity.objects.filter(slug=entry['slug']).first()
            by_name = Amenity.objects.filter(name__iexact=entry['name']).first()

            if by_slug and by_name and by_slug.pk != by_name.pk:
                # Slug and name belong to two different rows - never guess.
                skipped += 1
                self.stdout.write(self.style.WARNING(
                    f"Skipped '{entry['name']}': slug '{entry['slug']}' and name match different amenities."
                ))
                continue

            match = by_slug or by_name
            if match is None and entry['slug'] in LEGACY_ALIASES:
                match = Amenity.objects.filter(slug=LEGACY_ALIASES[entry['slug']]).first()

            if match is None:
                Amenity.objects.create(
                    name=entry['name'], slug=entry['slug'], category=entry['category'], is_active=True,
                )
                created += 1
                continue

            existing += 1
            if not match.is_active:
                inactive += 1  # preserved as-is: an admin deactivated it
            legacy_category = LEGACY_DEFAULT_CATEGORIES.get(match.slug)
            if match.category != entry['category'] and (not match.category or match.category == legacy_category):
                match.category = entry['category']
                match.save(update_fields=['category'])
                regrouped += 1

        types_created = types_existing = 0
        for entry in DEFAULT_PROPERTY_TYPES:
            # Case-insensitive name match: never create "Hotel" next to an existing "hotel"
            current = PropertyType.objects.filter(name__iexact=entry['name']).first()
            if current is None:
                PropertyType.objects.create(
                    name=entry['name'], description=entry['description'],
                    booking_mode=entry['booking_mode'], is_active=True,
                )
                types_created += 1
                continue
            # Existing type: left exactly as it is (name, active flag, booking mode)
            types_existing += 1
            if current.booking_mode != entry['booking_mode']:
                self.stdout.write(self.style.WARNING(
                    f"Property type '{current.name}' has booking_mode '{current.booking_mode}' "
                    f"(default is '{entry['booking_mode']}') - left unchanged."
                ))

        self.stdout.write(self.style.SUCCESS(
            f'Amenities: {created} created, {existing} already existing, {skipped} skipped '
            f'({regrouped} regrouped into master categories, {inactive} existing inactive left inactive). '
            f'{Amenity.objects.count()} total in database.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Property types: {types_created} created, {types_existing} already existing, 0 skipped. '
            f'{PropertyType.objects.count()} total in database.'
        ))
        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING('DRY RUN: all changes rolled back - nothing was saved.'))
