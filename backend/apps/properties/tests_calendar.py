"""
Tests for the owner availability calendar endpoints (P0-7):
calendar view, block-dates, unblock-dates on RoomTypeViewSet.

Run with: python manage.py test apps.properties.tests_calendar
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.models import Role, UserRole
from apps.bookings.models import Availability
from apps.bookings.service import BookingService
from .models import Property, PropertyType, RoomType, Pricing

User = get_user_model()


class OwnerCalendarTestCase(APITestCase):
    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        guest_role, _ = Role.objects.get_or_create(name='guest')

        self.owner_a = User.objects.create_user(email='cal-owner-a@example.com', password='test')
        UserRole.objects.create(user=self.owner_a, role=owner_role)
        self.owner_b = User.objects.create_user(email='cal-owner-b@example.com', password='test')
        UserRole.objects.create(user=self.owner_b, role=owner_role)
        self.guest = User.objects.create_user(email='cal-guest@example.com', password='test')
        UserRole.objects.create(user=self.guest, role=guest_role)

        property_type = PropertyType.objects.create(name='Calendar Villa Type')
        self.property = Property.objects.create(
            owner=self.owner_a, property_type=property_type, name='Calendar Villa',
            city='Colombo', district='Western', province='Western', status='approved'
        )
        self.room_type = RoomType.objects.create(
            property=self.property, name='Room', max_adults=2, total_occupancy=2, total_rooms=2
        )
        Pricing.objects.create(room_type=self.room_type, base_price=Decimal('5000.00'))

        self.check_in = date.today() + timedelta(days=10)
        self.check_out = self.check_in + timedelta(days=2)

    def test_owner_sees_booked_dates_in_calendar(self):
        BookingService.create_booking(
            room_type=self.room_type, guest=self.guest,
            check_in=self.check_in, check_out=self.check_out, num_adults=2
        )

        self.client.force_authenticate(self.owner_a)
        response = self.client.get(
            f'/api/properties/rooms/{self.room_type.id}/calendar/'
            f'?start_date={self.check_in.isoformat()}&end_date={(self.check_out + timedelta(days=1)).isoformat()}'
        )

        self.assertEqual(response.status_code, 200)
        days = response.data['data']['days']
        booked_day = next(d for d in days if d['date'] == self.check_in.isoformat())
        self.assertEqual(booked_day['booked_count'], 1)
        self.assertEqual(booked_day['available_count'], 1)  # total_rooms=2, 1 booked

    def test_calendar_counts_rooms_held_not_booking_rows(self):
        """A single 2-room booking must show the room type as fully booked."""
        BookingService.create_booking(
            room_type=self.room_type, guest=self.guest,
            check_in=self.check_in, check_out=self.check_out, num_adults=2, num_rooms=2
        )

        self.client.force_authenticate(self.owner_a)
        response = self.client.get(
            f'/api/properties/rooms/{self.room_type.id}/calendar/'
            f'?start_date={self.check_in.isoformat()}&end_date={self.check_out.isoformat()}'
        )

        booked_day = next(d for d in response.data['data']['days'] if d['date'] == self.check_in.isoformat())
        self.assertEqual(booked_day['booked_count'], 2)
        self.assertEqual(booked_day['available_count'], 0)

    def test_owner_can_block_and_unblock_dates(self):
        self.client.force_authenticate(self.owner_a)

        block_response = self.client.post(f'/api/properties/rooms/{self.room_type.id}/block-dates/', {
            'start_date': self.check_in.isoformat(),
            'end_date': self.check_out.isoformat(),
        }, format='json')
        self.assertEqual(block_response.status_code, 200)
        self.assertTrue(Availability.objects.filter(room_type=self.room_type, date=self.check_in, status='blocked').exists())

        calendar_response = self.client.get(
            f'/api/properties/rooms/{self.room_type.id}/calendar/'
            f'?start_date={self.check_in.isoformat()}&end_date={self.check_out.isoformat()}'
        )
        blocked_day = next(d for d in calendar_response.data['data']['days'] if d['date'] == self.check_in.isoformat())
        self.assertTrue(blocked_day['is_blocked'])
        self.assertEqual(blocked_day['available_count'], 0)

        unblock_response = self.client.post(f'/api/properties/rooms/{self.room_type.id}/unblock-dates/', {
            'start_date': self.check_in.isoformat(),
            'end_date': self.check_out.isoformat(),
        }, format='json')
        self.assertEqual(unblock_response.status_code, 200)
        self.assertFalse(
            Availability.objects.filter(room_type=self.room_type, date=self.check_in, status='blocked').exists()
        )

    def test_blocked_dates_prevent_new_bookings(self):
        """Confirms the calendar's block feature actually integrates with booking creation (P0-3)."""
        self.client.force_authenticate(self.owner_a)
        self.client.post(f'/api/properties/rooms/{self.room_type.id}/block-dates/', {
            'start_date': self.check_in.isoformat(),
            'end_date': self.check_out.isoformat(),
        }, format='json')

        self.client.force_authenticate(self.guest)
        response = self.client.post('/api/bookings/', {
            'room_type_id': str(self.room_type.id),
            'check_in_date': self.check_in.isoformat(),
            'check_out_date': self.check_out.isoformat(),
            'number_of_adults': 2,
        }, format='json')

        self.assertEqual(response.status_code, 409)

    def test_owner_b_cannot_view_owner_a_calendar(self):
        self.client.force_authenticate(self.owner_b)
        response = self.client.get(f'/api/properties/rooms/{self.room_type.id}/calendar/')
        self.assertEqual(response.status_code, 403)

    def test_owner_b_cannot_block_owner_a_room(self):
        self.client.force_authenticate(self.owner_b)
        response = self.client.post(f'/api/properties/rooms/{self.room_type.id}/block-dates/', {
            'start_date': self.check_in.isoformat(),
            'end_date': self.check_out.isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, 403)

    def test_guest_cannot_block_dates(self):
        self.client.force_authenticate(self.guest)
        response = self.client.post(f'/api/properties/rooms/{self.room_type.id}/block-dates/', {
            'start_date': self.check_in.isoformat(),
            'end_date': self.check_out.isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, 403)
