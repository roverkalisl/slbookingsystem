"""
Tests for booking system with critical double-booking prevention tests.

Run with: python manage.py test apps.bookings
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from datetime import date, timedelta
from decimal import Decimal
import threading
import time

from .models import Booking, BookingGuest, Availability
from .service import BookingService, BookingConflictError
from apps.properties.models import Property, PropertyType, RoomType, Pricing
from apps.core.models import Role, UserRole

User = get_user_model()


class BookingServiceTestCase(TransactionTestCase):
    """Tests for BookingService"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create roles
        cls.guest_role, _ = Role.objects.get_or_create(name='guest')
        cls.owner_role, _ = Role.objects.get_or_create(name='property_owner')

    def setUp(self):
        """Set up test data"""
        # Create users
        self.guest = User.objects.create_user(
            email='guest@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        UserRole.objects.create(user=self.guest, role=self.guest_role)

        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='testpass123',
            first_name='Property',
            last_name='Owner'
        )
        UserRole.objects.create(user=self.owner, role=self.owner_role)

        # Create property
        self.property_type = PropertyType.objects.create(name='Villa')
        self.property = Property.objects.create(
            owner=self.owner,
            property_type=self.property_type,
            name='Test Villa',
            city='Colombo',
            district='Western',
            province='Western',
            status='published'
        )

        # Create room type
        self.room_type = RoomType.objects.create(
            property=self.property,
            name='Deluxe Room',
            max_adults=2,
            total_occupancy=2,
            total_rooms=1  # Only 1 room available
        )

        # Create pricing
        self.pricing = Pricing.objects.create(
            room_type=self.room_type,
            base_price=Decimal('5000.00')
        )

        # Test dates
        self.check_in = date.today() + timedelta(days=7)
        self.check_out = self.check_in + timedelta(days=3)

    def test_create_booking_success(self):
        """Test successful booking creation"""
        booking = BookingService.create_booking(
            room_type=self.room_type,
            guest=self.guest,
            check_in=self.check_in,
            check_out=self.check_out,
            num_adults=2,
            num_children=0,
            guest_details=[{
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'is_primary_guest': True
            }]
        )

        # Assertions
        self.assertIsNotNone(booking)
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.guest, self.guest)
        self.assertEqual(booking.number_of_nights, 3)
        self.assertEqual(booking.total_price, Decimal('15000.00') + Decimal('750.00') + Decimal('1575.00'))

        # Check booking guest created
        guest_info = booking.guests.filter(is_primary_guest=True).first()
        self.assertIsNotNone(guest_info)
        self.assertEqual(guest_info.first_name, 'John')

    def test_double_booking_prevention(self):
        """Test that double bookings are prevented"""
        # Create first booking
        booking1 = BookingService.create_booking(
            room_type=self.room_type,
            guest=self.guest,
            check_in=self.check_in,
            check_out=self.check_out,
            num_adults=2
        )
        self.assertEqual(booking1.status, 'pending')

        # Try to create overlapping booking (should fail)
        with self.assertRaises(BookingConflictError):
            BookingService.create_booking(
                room_type=self.room_type,
                guest=self.guest,
                check_in=self.check_in + timedelta(days=1),  # Overlaps!
                check_out=self.check_out + timedelta(days=1),
                num_adults=2
            )

    def test_non_overlapping_bookings_allowed(self):
        """Test that non-overlapping bookings are allowed"""
        # First booking: days 7-10
        booking1 = BookingService.create_booking(
            room_type=self.room_type,
            guest=self.guest,
            check_in=self.check_in,
            check_out=self.check_out,
            num_adults=2
        )

        # Second booking: days 10-13 (no overlap - same checkout/checkin date)
        guest2 = User.objects.create_user(email='guest2@example.com', password='test')
        UserRole.objects.create(user=guest2, role=self.guest_role)

        booking2 = BookingService.create_booking(
            room_type=self.room_type,
            guest=guest2,
            check_in=self.check_out,  # Same as first booking's checkout
            check_out=self.check_out + timedelta(days=3),
            num_adults=2
        )

        # Both should succeed
        self.assertEqual(booking1.status, 'pending')
        self.assertEqual(booking2.status, 'pending')

    def test_check_availability_informational(self):
        """Test availability check (informational, non-blocking)"""
        # Create booking
        booking = BookingService.create_booking(
            room_type=self.room_type,
            guest=self.guest,
            check_in=self.check_in,
            check_out=self.check_out,
            num_adults=2
        )

        # Check availability (should show unavailable)
        is_available, available_count = BookingService.check_availability(
            self.room_type,
            self.check_in,
            self.check_out
        )

        self.assertFalse(is_available)
        self.assertEqual(available_count, 0)

    def test_cancellation_and_availability_release(self):
        """Test booking cancellation and availability release"""
        # Create booking
        booking = BookingService.create_booking(
            room_type=self.room_type,
            guest=self.guest,
            check_in=self.check_in,
            check_out=self.check_out,
            num_adults=2
        )

        # Cancel booking
        result = BookingService.cancel_booking(booking)

        self.assertEqual(result['status'], 'cancelled')
        self.assertGreater(result['refund_amount'], Decimal('0'))

        # Check availability (should be available again)
        is_available, available_count = BookingService.check_availability(
            self.room_type,
            self.check_in,
            self.check_out
        )

        self.assertTrue(is_available)
        self.assertEqual(available_count, 1)

    def test_invalid_date_range_rejected(self):
        """Test that invalid date ranges are rejected"""
        with self.assertRaises(ValueError):
            BookingService.create_booking(
                room_type=self.room_type,
                guest=self.guest,
                check_in=self.check_out,
                check_out=self.check_in,  # Reversed!
                num_adults=2
            )

    def test_occupancy_validation(self):
        """Test that occupancy limits are enforced"""
        # Try to book with too many guests
        with self.assertRaises(ValueError):
            BookingService.create_booking(
                room_type=self.room_type,
                guest=self.guest,
                check_in=self.check_in,
                check_out=self.check_out,
                num_adults=5,  # Room only fits 2
                num_children=0
            )


class ConcurrentBookingTestCase(TransactionTestCase):
    """Tests for concurrent booking scenarios (double-booking prevention)"""

    def setUp(self):
        """Set up test data"""
        guest_role, _ = Role.objects.get_or_create(name='guest')
        owner_role, _ = Role.objects.get_or_create(name='property_owner')

        self.guest1 = User.objects.create_user(email='guest1@example.com', password='test')
        self.guest2 = User.objects.create_user(email='guest2@example.com', password='test')
        UserRole.objects.create(user=self.guest1, role=guest_role)
        UserRole.objects.create(user=self.guest2, role=guest_role)

        self.owner = User.objects.create_user(email='owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)

        property_type = PropertyType.objects.create(name='Villa')
        self.property = Property.objects.create(
            owner=self.owner,
            property_type=property_type,
            name='Test Villa',
            city='Colombo',
            district='Western',
            province='Western',
            status='published'
        )

        self.room_type = RoomType.objects.create(
            property=self.property,
            name='Room',
            max_adults=2,
            total_occupancy=2,
            total_rooms=1
        )

        Pricing.objects.create(
            room_type=self.room_type,
            base_price=Decimal('5000.00')
        )

        self.check_in = date.today() + timedelta(days=7)
        self.check_out = self.check_in + timedelta(days=3)
        self.booking_results = []
        self.booking_errors = []

    def _book_room(self, guest):
        """Helper to book room in thread"""
        try:
            booking = BookingService.create_booking(
                room_type=self.room_type,
                guest=guest,
                check_in=self.check_in,
                check_out=self.check_out,
                num_adults=2
            )
            self.booking_results.append(booking)
        except BookingConflictError as e:
            self.booking_errors.append(str(e))

    def test_concurrent_bookings_safe(self):
        """Test concurrent booking attempts (double-booking prevention)"""
        # Create two threads that try to book same room simultaneously
        thread1 = threading.Thread(target=self._book_room, args=(self.guest1,))
        thread2 = threading.Thread(target=self._book_room, args=(self.guest2,))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Exactly one booking should succeed, one should fail
        self.assertEqual(len(self.booking_results), 1)
        self.assertEqual(len(self.booking_errors), 1)
        self.assertIn("not available", self.booking_errors[0])


class BookingRefundTestCase(TestCase):
    """Tests for booking cancellation and refunds"""

    def setUp(self):
        """Set up test data"""
        guest_role, _ = Role.objects.get_or_create(name='guest')
        owner_role, _ = Role.objects.get_or_create(name='property_owner')

        self.guest = User.objects.create_user(email='guest@example.com', password='test')
        UserRole.objects.create(user=self.guest, role=guest_role)

        self.owner = User.objects.create_user(email='owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)

        property_type = PropertyType.objects.create(name='Villa')
        self.property = Property.objects.create(
            owner=self.owner,
            property_type=property_type,
            name='Test Villa',
            city='Colombo',
            district='Western',
            province='Western',
            status='published'
        )

        self.room_type = RoomType.objects.create(
            property=self.property,
            name='Room',
            max_adults=2,
            total_occupancy=2,
            total_rooms=1
        )

        Pricing.objects.create(
            room_type=self.room_type,
            base_price=Decimal('5000.00')
        )

    def test_full_refund_7_days_before(self):
        """Test full refund for cancellation 7+ days before"""
        check_in = date.today() + timedelta(days=10)
        check_out = check_in + timedelta(days=3)

        booking = BookingService.create_booking(
            room_type=self.room_type,
            guest=self.guest,
            check_in=check_in,
            check_out=check_out,
            num_adults=2
        )

        result = BookingService.cancel_booking(booking)

        # Should get 100% refund (10 days before)
        self.assertEqual(result['refund_percent'], Decimal('100'))
        self.assertEqual(result['refund_amount'], booking.total_price)

    def test_partial_refund_3_days_before(self):
        """Test partial refund for cancellation 3-7 days before"""
        check_in = date.today() + timedelta(days=5)
        check_out = check_in + timedelta(days=3)

        booking = BookingService.create_booking(
            room_type=self.room_type,
            guest=self.guest,
            check_in=check_in,
            check_out=check_out,
            num_adults=2
        )

        result = BookingService.cancel_booking(booking)

        # Should get 50% refund (5 days before)
        self.assertEqual(result['refund_percent'], Decimal('50'))
        self.assertAlmostEqual(
            result['refund_amount'],
            booking.total_price * Decimal('0.5'),
            places=2
        )

    def test_no_refund_less_than_3_days(self):
        """Test no refund for cancellation less than 3 days before"""
        check_in = date.today() + timedelta(days=1)
        check_out = check_in + timedelta(days=3)

        booking = BookingService.create_booking(
            room_type=self.room_type,
            guest=self.guest,
            check_in=check_in,
            check_out=check_out,
            num_adults=2
        )

        result = BookingService.cancel_booking(booking)

        # Should get 0% refund (1 day before)
        self.assertEqual(result['refund_percent'], Decimal('0'))
        self.assertEqual(result['refund_amount'], Decimal('0'))
