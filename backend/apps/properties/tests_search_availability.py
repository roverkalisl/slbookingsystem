"""
Tests for date-based availability filtering in property search.

Availability follows the booking architecture: rooms are bookable by default
(daily Availability rows only record owner blocks and booked dates), blocked
or maintenance dates exclude a room, and inventory is the SUM of
number_of_rooms held by overlapping active bookings.

Run with: python manage.py test apps.properties.tests_search_availability
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.bookings.models import Availability
from apps.bookings.service import BookingService
from apps.core.models import Role, UserRole
from .models import Property, PropertyType, RoomType, Pricing
from .search import PropertySearchService

User = get_user_model()


class SearchAvailabilityTestCase(APITestCase):
    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.owner = User.objects.create_user(email='search-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.guest = User.objects.create_user(email='search-guest@example.com', password='test')
        UserRole.objects.create(user=self.guest, role=guest_role)
        self.property_type = PropertyType.objects.create(name='Search Availability Type')

        self.check_in = date.today() + timedelta(days=20)
        self.check_out = self.check_in + timedelta(days=2)

    def make_property(self, name, total_rooms=1, status='approved'):
        property_obj = Property.objects.create(
            owner=self.owner, property_type=self.property_type, name=name,
            description='desc', city='Ella', district='Badulla', province='Uva', status=status
        )
        room = RoomType.objects.create(
            property=property_obj, name=f'{name} Room', max_adults=2, total_occupancy=2, total_rooms=total_rooms
        )
        Pricing.objects.create(room_type=room, base_price=Decimal('8000.00'))
        return property_obj, room

    def search(self, check_in=None, check_out=None):
        service = PropertySearchService().filter_by_availability(check_in or self.check_in, check_out or self.check_out)
        return set(service.queryset.values_list('name', flat=True))

    def test_available_property_appears(self):
        self.make_property('Open Villa')
        self.assertIn('Open Villa', self.search())

    def test_missing_daily_records_mean_available_not_excluded(self):
        """No Availability rows at all (no bookings, no blocks) = bookable by default."""
        _, room = self.make_property('Fresh Villa')
        self.assertFalse(Availability.objects.filter(room_type=room).exists())
        self.assertIn('Fresh Villa', self.search())

    def test_missing_daily_records_do_not_hide_full_bookings(self):
        """Availability rows are not the source of truth - bookings are.
        A fully booked room must be excluded even if its daily rows are gone."""
        _, room = self.make_property('Booked Villa')
        BookingService.create_booking(
            room_type=room, guest=self.guest, check_in=self.check_in, check_out=self.check_out, num_adults=1
        )
        Availability.objects.filter(room_type=room).delete()
        self.assertNotIn('Booked Villa', self.search())

    def test_fully_booked_property_does_not_appear(self):
        _, room = self.make_property('Full Hotel', total_rooms=2)
        BookingService.create_booking(
            room_type=room, guest=self.guest, check_in=self.check_in, check_out=self.check_out,
            num_adults=1, num_rooms=2
        )
        self.assertNotIn('Full Hotel', self.search())

    def test_partially_booked_property_still_appears(self):
        _, room = self.make_property('Half Hotel', total_rooms=3)
        BookingService.create_booking(
            room_type=room, guest=self.guest, check_in=self.check_in, check_out=self.check_out,
            num_adults=1, num_rooms=2
        )
        self.assertIn('Half Hotel', self.search())

    def test_cancelled_booking_frees_property_in_search(self):
        _, room = self.make_property('Freed Villa')
        booking = BookingService.create_booking(
            room_type=room, guest=self.guest, check_in=self.check_in, check_out=self.check_out, num_adults=1
        )
        BookingService.cancel_booking(booking)
        self.assertIn('Freed Villa', self.search())

    def test_blocked_dates_do_not_appear(self):
        _, room = self.make_property('Blocked Villa', total_rooms=2)
        Availability.objects.create(
            room_type=room, date=self.check_in + timedelta(days=1), status='blocked', available_count=0
        )
        self.assertNotIn('Blocked Villa', self.search())

    def test_block_outside_range_does_not_hide_property(self):
        _, room = self.make_property('Later Block Villa')
        Availability.objects.create(
            room_type=room, date=self.check_out, status='blocked', available_count=0  # check-out day is free
        )
        self.assertIn('Later Block Villa', self.search())

    def test_booked_status_row_alone_is_not_treated_as_available(self):
        """A leftover 'booked' daily row must not make a full room look available."""
        _, room = self.make_property('Stale Row Villa')
        BookingService.create_booking(
            room_type=room, guest=self.guest, check_in=self.check_in, check_out=self.check_out, num_adults=1
        )
        self.assertTrue(Availability.objects.filter(room_type=room, status='booked').exists())
        self.assertNotIn('Stale Row Villa', self.search())

    def test_other_room_type_keeps_property_available(self):
        property_obj, room = self.make_property('Two Room Hotel')
        spare = RoomType.objects.create(
            property=property_obj, name='Spare Room', max_adults=2, total_occupancy=2, total_rooms=1
        )
        Pricing.objects.create(room_type=spare, base_price=Decimal('9000.00'))
        BookingService.create_booking(
            room_type=room, guest=self.guest, check_in=self.check_in, check_out=self.check_out, num_adults=1
        )
        self.assertIn('Two Room Hotel', self.search())

    def test_inactive_room_does_not_make_property_available(self):
        _, room = self.make_property('Closed Villa')
        room.is_active = False
        room.save()
        self.assertNotIn('Closed Villa', self.search())

    def test_unapproved_property_never_appears(self):
        self.make_property('Draft Villa', status='draft')
        self.assertNotIn('Draft Villa', self.search())

    def test_search_api_applies_availability(self):
        self.make_property('Api Open Villa')
        _, full_room = self.make_property('Api Full Villa')
        BookingService.create_booking(
            room_type=full_room, guest=self.guest, check_in=self.check_in, check_out=self.check_out, num_adults=1
        )

        response = self.client.get(
            f'/api/properties/search/advanced/?city=Ella&check_in={self.check_in.isoformat()}'
            f'&check_out={self.check_out.isoformat()}'
        )
        self.assertEqual(response.status_code, 200, response.content)
        results = response.data.get('results') or response.data.get('data') or []
        if isinstance(results, dict):
            results = results.get('results', [])
        names = {item['name'] for item in results}
        self.assertIn('Api Open Villa', names)
        self.assertNotIn('Api Full Villa', names)
