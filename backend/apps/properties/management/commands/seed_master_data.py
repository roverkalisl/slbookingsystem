"""
Idempotent seed for master data (Amenity, PropertyType) that the frontend
depends on being non-empty (e.g. GET /api/properties/amenities/).

Unlike `loaddata`, which keys on numeric primary keys and would either
collide with or silently overwrite whatever already has those same IDs in
production, this command matches on stable logical identity - Amenity.slug
and PropertyType.name - and only ever creates rows that are missing.
Anything already in the database (including hand-added/customised records
like a production "Entry Villa" PropertyType) is left completely untouched.

Safe to run repeatedly and safe to run against a database that already has
data: run again after adding a new default here to top up only what's new.

Run with: python manage.py seed_master_data
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.properties.models import Amenity, PropertyType


DEFAULT_AMENITIES = [
    {'name': 'WiFi', 'slug': 'wifi', 'category': 'connectivity'},
    {'name': 'Swimming Pool', 'slug': 'swimming-pool', 'category': 'recreation'},
    {'name': 'Parking', 'slug': 'parking', 'category': 'general'},
    {'name': 'Air Conditioning', 'slug': 'air-conditioning', 'category': 'room'},
    {'name': 'Kitchen', 'slug': 'kitchen', 'category': 'general'},
    {'name': 'Restaurant', 'slug': 'restaurant', 'category': 'dining'},
    {'name': 'Breakfast Included', 'slug': 'breakfast-included', 'category': 'dining'},
    {'name': 'Garden', 'slug': 'garden', 'category': 'recreation'},
    {'name': 'Beach Access', 'slug': 'beach-access', 'category': 'recreation'},
    {'name': 'Hot Water', 'slug': 'hot-water', 'category': 'room'},
    {'name': 'TV', 'slug': 'tv', 'category': 'room'},
    {'name': 'Washing Machine', 'slug': 'washing-machine', 'category': 'general'},
    {'name': 'Airport Transfer', 'slug': 'airport-transfer', 'category': 'services'},
    {'name': 'BBQ', 'slug': 'bbq', 'category': 'recreation'},
    {'name': 'Private Pool', 'slug': 'private-pool', 'category': 'recreation'},
    {'name': 'Balcony', 'slug': 'balcony', 'category': 'room'},
    {'name': 'Sea View', 'slug': 'sea-view', 'category': 'room'},
    {'name': 'Mountain View', 'slug': 'mountain-view', 'category': 'room'},
    {'name': 'Room Service', 'slug': 'room-service', 'category': 'services'},
    {'name': 'Bar', 'slug': 'bar', 'category': 'dining'},
    {'name': 'Gym / Fitness Center', 'slug': 'gym-fitness-center', 'category': 'recreation'},
    {'name': 'Spa', 'slug': 'spa', 'category': 'recreation'},
    {'name': 'Pet Friendly', 'slug': 'pet-friendly', 'category': 'general'},
    {'name': 'Elevator', 'slug': 'elevator', 'category': 'general'},
    {'name': '24-Hour Front Desk', 'slug': '24-hour-front-desk', 'category': 'services'},
]

DEFAULT_PROPERTY_TYPES = [
    {'name': 'Villa', 'description': None},
    {'name': 'Hotel', 'description': None},
    {'name': 'Guest House', 'description': None},
    {'name': 'Apartment', 'description': None},
    {'name': 'Holiday Home', 'description': None},
    {'name': 'Resort', 'description': None},
    {'name': 'Bungalow', 'description': None},
    {'name': 'Homestay', 'description': None},
]


class Command(BaseCommand):
    help = 'Idempotently seed default Amenity and PropertyType records without touching existing data.'

    @transaction.atomic
    def handle(self, *args, **options):
        amenities_created = 0
        for entry in DEFAULT_AMENITIES:
            _, created = Amenity.objects.get_or_create(
                slug=entry['slug'],
                defaults={'name': entry['name'], 'category': entry['category'], 'is_active': True},
            )
            if created:
                amenities_created += 1

        types_created = 0
        for entry in DEFAULT_PROPERTY_TYPES:
            _, created = PropertyType.objects.get_or_create(
                name=entry['name'],
                defaults={'description': entry['description'], 'is_active': True},
            )
            if created:
                types_created += 1

        total_amenities = Amenity.objects.count()
        total_types = PropertyType.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f'Amenities: created {amenities_created} new, {total_amenities} total in database.'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Property types: created {types_created} new, {total_types} total in database.'
        ))
