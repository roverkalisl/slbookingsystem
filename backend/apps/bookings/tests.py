"""
Tests for booking system with critical double-booking prevention tests.

Run with: python manage.py test apps.bookings
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from django.core import mail
from django.db import connection
from django.db.utils import OperationalError
from datetime import date, timedelta
from decimal import Decimal
from rest_framework.test import APIClient
import random
import threading
import time

from .models import Booking, BookingGuest, Availability
from .service import BookingService, BookingConflictError
from apps.properties.models import Property, PropertyType, RoomType, Pricing
from apps.properties.pricing import PricingCalculator
from apps.core.models import Role, UserRole

User = get_user_model()


class BookingServiceTestCase(TransactionTestCase):
    """Tests for BookingService"""

    def setUp(self):
        """Set up test data.

        NOTE: roles are (re)created here, not in setUpClass. TransactionTestCase
        truncates all tables after every test, so anything seeded once in
        setUpClass (e.g. shared Role rows) is gone by the second test method,
        causing every subsequent test to fail with a FOREIGN KEY constraint
        error on UserRole. get_or_create makes this safe to repeat per-test.
        """
        self.guest_role, _ = Role.objects.get_or_create(name='guest')
        self.owner_role, _ = Role.objects.get_or_create(name='property_owner')

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
            status='approved'
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
            status='approved'
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
        self.booking_errors = []  # genuine BookingConflictError only
        self.lock_errors = []  # SQLite engine lock contention (never a booking outcome)

    MAX_LOCK_RETRIES = 20

    def _book_room(self, guest):
        """Helper to book room in thread.

        SQLite-only note: unlike PostgreSQL (what production runs), SQLite
        has no real row-level locking. Two threads racing select_for_update()
        against a shared in-memory test database can collide with
        SQLITE_LOCKED ("database table is locked"), which the connection's
        busy_timeout does not retry (that only covers SQLITE_BUSY). This is
        an artifact of the test database engine, not of the application's
        own locking logic - PostgreSQL correctly blocks the second
        transaction until the first commits instead of erroring.

        Lock errors are retried with jittered backoff and are recorded
        separately - they are NEVER counted as a booking conflict, so the
        test only passes when the application itself rejected the loser.
        On PostgreSQL an OperationalError is a real failure and is re-raised.
        """
        try:
            for attempt in range(self.MAX_LOCK_RETRIES):
                try:
                    booking = BookingService.create_booking(
                        room_type=self.room_type,
                        guest=guest,
                        check_in=self.check_in,
                        check_out=self.check_out,
                        num_adults=2
                    )
                    self.booking_results.append(booking)
                    return
                except BookingConflictError as e:
                    self.booking_errors.append(str(e))
                    return
                except OperationalError as e:
                    if connection.vendor != 'sqlite':
                        raise
                    if attempt == self.MAX_LOCK_RETRIES - 1:
                        self.lock_errors.append(str(e))
                        return
                    time.sleep(random.uniform(0.02, 0.1) * (attempt + 1))
        finally:
            connection.close()

    def test_concurrent_bookings_safe(self):
        """Test concurrent booking attempts (double-booking prevention).

        True concurrency validation of SELECT FOR UPDATE must be run against
        PostgreSQL (production engine). On SQLite this test still verifies the
        application-level invariant, but a run where engine lock contention
        prevents a verdict is reported as skipped (inconclusive), not passed.
        """
        # Create two threads that try to book same room simultaneously
        thread1 = threading.Thread(target=self._book_room, args=(self.guest1,))
        thread2 = threading.Thread(target=self._book_room, args=(self.guest2,))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Hard invariant on every engine and every run: never a double booking.
        self.assertLessEqual(len(self.booking_results), 1)
        self.assertLessEqual(Booking.objects.filter(room_type=self.room_type).count(), 1)

        if self.lock_errors:
            self.skipTest(
                f"Inconclusive on SQLite: engine lock contention persisted after "
                f"{self.MAX_LOCK_RETRIES} retries ({len(self.lock_errors)} thread(s)). "
                f"No double booking occurred. Run against PostgreSQL for true concurrency validation."
            )

        # Exactly one booking should succeed and the other must be rejected by
        # the application's own availability check (a real BookingConflictError).
        self.assertEqual(len(self.booking_results), 1)
        self.assertEqual(len(self.booking_errors), 1)


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
            status='approved'
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


class OwnerBookingManagementTestCase(TransactionTestCase):
    """Tests for owner confirm/reject actions, notification wiring, and ownership security"""

    def setUp(self):
        # Roles recreated per-test: TransactionTestCase truncates tables after
        # every test, so a setUpClass-seeded Role would only survive the first
        # test method (see BookingServiceTestCase.setUp for the full story).
        self.guest_role, _ = Role.objects.get_or_create(name='guest')
        self.owner_role, _ = Role.objects.get_or_create(name='property_owner')

        self.guest = User.objects.create_user(email='guest2@example.com', password='testpass123', first_name='Jane', last_name='Doe')
        UserRole.objects.create(user=self.guest, role=self.guest_role)

        self.owner_a = User.objects.create_user(email='ownerA@example.com', password='testpass123', first_name='Owner', last_name='A')
        UserRole.objects.create(user=self.owner_a, role=self.owner_role)

        self.owner_b = User.objects.create_user(email='ownerB@example.com', password='testpass123', first_name='Owner', last_name='B')
        UserRole.objects.create(user=self.owner_b, role=self.owner_role)

        property_type = PropertyType.objects.create(name='Hotel')
        self.property = Property.objects.create(
            owner=self.owner_a, property_type=property_type, name='Owner A Hotel',
            city='Kandy', district='Central', province='Central', status='approved'
        )
        self.room_type = RoomType.objects.create(
            property=self.property, name='Standard Room', max_adults=2, total_occupancy=2, total_rooms=2
        )
        Pricing.objects.create(room_type=self.room_type, base_price=Decimal('4000.00'))

        self.check_in = date.today() + timedelta(days=10)
        self.check_out = self.check_in + timedelta(days=2)

        self.booking = BookingService.create_booking(
            room_type=self.room_type, guest=self.guest,
            check_in=self.check_in, check_out=self.check_out, num_adults=2
        )

    def test_owner_confirm_booking_success(self):
        """Owner can confirm their own pending booking; guest receives an email"""
        mail.outbox = []
        updated = BookingService.owner_confirm_booking(self.booking)
        self.assertEqual(updated.status, 'confirmed')

    def test_owner_confirm_wrong_status_fails(self):
        """Confirming a non-pending booking raises ValueError"""
        BookingService.owner_confirm_booking(self.booking)
        with self.assertRaises(ValueError):
            BookingService.owner_confirm_booking(self.booking)

    def test_owner_reject_booking_releases_availability(self):
        """Rejecting a booking sets status=rejected and releases the room back to available"""
        available_before = Availability.objects.filter(
            room_type=self.room_type, date__gte=self.check_in, date__lt=self.check_out
        ).values_list('status', flat=True)
        self.assertTrue(all(s == 'booked' for s in available_before) or len(list(available_before)) == 0)

        updated = BookingService.owner_reject_booking(self.booking, reason='Room under maintenance')
        self.assertEqual(updated.status, 'rejected')

        available_after = Availability.objects.filter(
            room_type=self.room_type, date__gte=self.check_in, date__lt=self.check_out
        ).values_list('status', flat=True)
        self.assertTrue(all(s == 'available' for s in available_after))

    def test_new_booking_notification_sent_on_create(self):
        """Creating a booking via the API sends the owner a real, renderable email"""
        mail.outbox = []
        client = APIClient()
        client.force_authenticate(user=self.guest)
        response = client.post('/api/bookings/', {
            'room_type_id': str(self.room_type.id),
            'check_in_date': str(self.check_in + timedelta(days=20)),
            'check_out_date': str(self.check_in + timedelta(days=22)),
            'number_of_adults': 2,
            'number_of_children': 0,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.owner_a.email, mail.outbox[0].to)

    def test_confirm_endpoint_sends_confirmation_email(self):
        """POST /api/bookings/{id}/confirm/ renders the template and emails the guest"""
        mail.outbox = []
        client = APIClient()
        client.force_authenticate(user=self.owner_a)
        response = client.post(f'/api/bookings/{self.booking.id}/confirm/')
        self.assertEqual(response.status_code, 200, response.content)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.guest.email, mail.outbox[0].to)

    def test_reject_endpoint_sends_rejection_email(self):
        """POST /api/bookings/{id}/reject/ renders the template and emails the guest"""
        mail.outbox = []
        client = APIClient()
        client.force_authenticate(user=self.owner_a)
        response = client.post(f'/api/bookings/{self.booking.id}/reject/', {'reason': 'Fully booked'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'rejected')
        self.assertEqual(len(mail.outbox), 1)

    def test_owner_b_cannot_confirm_owner_a_booking(self):
        """Object-level security: Owner B must not be able to confirm Owner A's booking"""
        client = APIClient()
        client.force_authenticate(user=self.owner_b)
        response = client.post(f'/api/bookings/{self.booking.id}/confirm/')
        self.assertEqual(response.status_code, 403)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'pending')

    def test_owner_b_cannot_reject_owner_a_booking(self):
        """Object-level security: Owner B must not be able to reject Owner A's booking"""
        client = APIClient()
        client.force_authenticate(user=self.owner_b)
        response = client.post(f'/api/bookings/{self.booking.id}/reject/', {'reason': 'x'}, format='json')
        self.assertEqual(response.status_code, 403)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'pending')

    def test_guest_cannot_confirm_own_booking(self):
        """Guests are not owners and must not be able to confirm bookings"""
        client = APIClient()
        client.force_authenticate(user=self.guest)
        response = client.post(f'/api/bookings/{self.booking.id}/confirm/')
        self.assertEqual(response.status_code, 403)

    def test_owner_a_cannot_view_owner_b_property_bookings_list(self):
        """Object-level security: Owner A's booking list must not include Owner B's properties' bookings"""
        other_property = Property.objects.create(
            owner=self.owner_b, property_type=self.property.property_type, name='Owner B Villa',
            city='Galle', district='Southern', province='Southern', status='approved'
        )
        other_room = RoomType.objects.create(
            property=other_property, name='Room', max_adults=2, total_occupancy=2, total_rooms=1
        )
        Pricing.objects.create(room_type=other_room, base_price=Decimal('3000.00'))
        other_booking = BookingService.create_booking(
            room_type=other_room, guest=self.guest,
            check_in=self.check_in, check_out=self.check_out, num_adults=1
        )

        client = APIClient()
        client.force_authenticate(user=self.owner_a)
        response = client.get('/api/bookings/')
        self.assertEqual(response.status_code, 200)
        returned_ids = [b['id'] for b in response.data.get('results', response.data.get('data', response.data))]
        self.assertNotIn(str(other_booking.id), returned_ids)


class AvailabilityValidationTestCase(TransactionTestCase):
    """
    P0-3: the backend must be the final authority on availability, checking
    property/room active status, past dates, capacity, inventory, and
    owner-blocked dates - never trusting only a frontend pre-check.
    """

    def setUp(self):
        guest_role, _ = Role.objects.get_or_create(name='guest')
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.guest = User.objects.create_user(email='avail-guest@example.com', password='test')
        UserRole.objects.create(user=self.guest, role=guest_role)
        self.owner = User.objects.create_user(email='avail-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)

        property_type = PropertyType.objects.create(name='Availability Villa Type')
        self.property = Property.objects.create(
            owner=self.owner, property_type=property_type, name='Availability Villa',
            city='Colombo', district='Western', province='Western', status='approved'
        )
        self.room_type = RoomType.objects.create(
            property=self.property, name='Room', max_adults=2, total_occupancy=2, total_rooms=1
        )
        Pricing.objects.create(room_type=self.room_type, base_price=Decimal('5000.00'))

        self.check_in = date.today() + timedelta(days=10)
        self.check_out = self.check_in + timedelta(days=2)

    def test_cannot_book_unapproved_property(self):
        self.property.status = 'pending_approval'
        self.property.save()

        with self.assertRaises(BookingConflictError):
            BookingService.create_booking(
                room_type=self.room_type, guest=self.guest,
                check_in=self.check_in, check_out=self.check_out, num_adults=2
            )

    def test_cannot_book_inactive_room(self):
        self.room_type.is_active = False
        self.room_type.save()

        with self.assertRaises(BookingConflictError):
            BookingService.create_booking(
                room_type=self.room_type, guest=self.guest,
                check_in=self.check_in, check_out=self.check_out, num_adults=2
            )

    def test_cannot_book_checkin_in_the_past(self):
        with self.assertRaises(ValueError):
            BookingService.create_booking(
                room_type=self.room_type, guest=self.guest,
                check_in=date.today() - timedelta(days=1),
                check_out=date.today() + timedelta(days=1), num_adults=2
            )

    def test_cannot_book_owner_blocked_dates(self):
        Availability.objects.create(
            room_type=self.room_type, date=self.check_in, status='blocked', available_count=0
        )

        with self.assertRaises(BookingConflictError):
            BookingService.create_booking(
                room_type=self.room_type, guest=self.guest,
                check_in=self.check_in, check_out=self.check_out, num_adults=2
            )

    def test_api_returns_409_with_detail_message_on_conflict(self):
        """Spec: 409 response must include a 'detail' key, not just a generic error."""
        client = APIClient()
        client.force_authenticate(user=self.guest)

        # First booking succeeds and takes the only room
        first = client.post('/api/bookings/', {
            'room_type_id': str(self.room_type.id),
            'check_in_date': str(self.check_in),
            'check_out_date': str(self.check_out),
            'number_of_adults': 2,
        }, format='json')
        self.assertEqual(first.status_code, 201)

        # Second overlapping booking must be rejected with 409 + detail
        second = client.post('/api/bookings/', {
            'room_type_id': str(self.room_type.id),
            'check_in_date': str(self.check_in),
            'check_out_date': str(self.check_out),
            'number_of_adults': 1,
        }, format='json')
        self.assertEqual(second.status_code, 409)
        self.assertIn('detail', second.data)
        self.assertTrue(len(second.data['detail']) > 0)


class MultiRoomInventoryTestCase(TestCase):
    """
    Regression: inventory must be the SUM of number_of_rooms held by
    overlapping active bookings, not the number of booking rows. Previously a
    single 3-room booking consumed only 1 slot, allowing overbooking.
    """

    def setUp(self):
        guest_role, _ = Role.objects.get_or_create(name='guest')
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.guest1 = User.objects.create_user(email='multi-guest1@example.com', password='test')
        self.guest2 = User.objects.create_user(email='multi-guest2@example.com', password='test')
        UserRole.objects.create(user=self.guest1, role=guest_role)
        UserRole.objects.create(user=self.guest2, role=guest_role)
        self.owner = User.objects.create_user(email='multi-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)

        property_type = PropertyType.objects.create(name='Multi-room Hotel Type')
        self.property = Property.objects.create(
            owner=self.owner, property_type=property_type, name='Multi-room Hotel',
            city='Kandy', district='Kandy', province='Central', status='approved'
        )
        self.room_type = RoomType.objects.create(
            property=self.property, name='Standard', max_adults=2, total_occupancy=2, total_rooms=3
        )
        Pricing.objects.create(room_type=self.room_type, base_price=Decimal('5000.00'))

        self.check_in = date.today() + timedelta(days=14)
        self.check_out = self.check_in + timedelta(days=2)

    def _book(self, guest, num_rooms, room_type=None, check_in=None, check_out=None):
        return BookingService.create_booking(
            room_type=room_type or self.room_type,
            guest=guest,
            check_in=check_in or self.check_in,
            check_out=check_out or self.check_out,
            num_adults=1,
            num_rooms=num_rooms,
        )

    def test_three_rooms_booked_then_one_more_is_rejected(self):
        self._book(self.guest1, 3)
        with self.assertRaises(BookingConflictError):
            self._book(self.guest2, 1)
        self.assertEqual(Booking.objects.filter(room_type=self.room_type).count(), 1)

    def test_two_rooms_booked_then_one_more_is_accepted(self):
        self._book(self.guest1, 2)
        booking = self._book(self.guest2, 1)
        self.assertEqual(booking.number_of_rooms, 1)
        self.assertEqual(Booking.objects.filter(room_type=self.room_type).count(), 2)

    def test_two_rooms_booked_then_two_more_is_rejected(self):
        self._book(self.guest1, 2)
        with self.assertRaises(BookingConflictError):
            self._book(self.guest2, 2)

    def test_cancelled_booking_releases_its_room_quantity(self):
        booking = self._book(self.guest1, 3)
        BookingService.cancel_booking(booking)

        replacement = self._book(self.guest2, 3)
        self.assertEqual(replacement.number_of_rooms, 3)

    def test_rejected_booking_releases_its_room_quantity(self):
        booking = self._book(self.guest1, 3)
        BookingService.owner_reject_booking(booking, reason='Unavailable')

        replacement = self._book(self.guest2, 3)
        self.assertEqual(replacement.number_of_rooms, 3)

    def test_other_room_types_are_independent(self):
        other_room = RoomType.objects.create(
            property=self.property, name='Suite', max_adults=2, total_occupancy=2, total_rooms=1
        )
        Pricing.objects.create(room_type=other_room, base_price=Decimal('9000.00'))

        self._book(self.guest1, 3)
        booking = self._book(self.guest2, 1, room_type=other_room)
        self.assertEqual(booking.room_type, other_room)

    def test_non_overlapping_dates_remain_bookable(self):
        self._book(self.guest1, 3)
        # Check-out day is exclusive, so a stay starting on it does not overlap.
        booking = self._book(
            self.guest2, 3,
            check_in=self.check_out, check_out=self.check_out + timedelta(days=2)
        )
        self.assertEqual(booking.number_of_rooms, 3)

    def test_check_availability_counts_rooms_not_rows(self):
        self._book(self.guest1, 2)
        is_available, available_count = BookingService.check_availability(
            self.room_type, self.check_in, self.check_out
        )
        self.assertTrue(is_available)
        self.assertEqual(available_count, 1)

    def test_availability_count_tracks_room_quantity(self):
        booking = self._book(self.guest1, 2)
        record = Availability.objects.get(room_type=self.room_type, date=self.check_in)
        self.assertEqual(record.available_count, 1)

        BookingService.cancel_booking(booking)
        record.refresh_from_db()
        self.assertEqual(record.available_count, 3)

    def test_releasing_booking_does_not_unblock_owner_blocked_date(self):
        booking = self._book(self.guest1, 1)
        Availability.objects.filter(room_type=self.room_type, date=self.check_in).update(status='blocked')

        BookingService.cancel_booking(booking)
        record = Availability.objects.get(room_type=self.room_type, date=self.check_in)
        self.assertEqual(record.status, 'blocked')

    def test_api_rejects_multi_room_overbooking_with_409(self):
        client = APIClient()
        client.force_authenticate(user=self.guest1)
        payload = {
            'room_type_id': str(self.room_type.id),
            'check_in_date': str(self.check_in),
            'check_out_date': str(self.check_out),
            'number_of_adults': 1,
        }
        first = client.post('/api/bookings/', {**payload, 'number_of_rooms': 3}, format='json')
        self.assertEqual(first.status_code, 201)

        client.force_authenticate(user=self.guest2)
        second = client.post('/api/bookings/', {**payload, 'number_of_rooms': 1}, format='json')
        self.assertEqual(second.status_code, 409)


def _next_weekday(weekday: int, min_days_ahead: int = 14) -> date:
    """First date at least min_days_ahead from today falling on weekday (Mon=0)."""
    start = date.today() + timedelta(days=min_days_ahead)
    return start + timedelta(days=(weekday - start.weekday()) % 7)


class MultiRoomTestMixin:
    """Shared fixture: approved property, room priced 10,000/night (5% fee, 10% tax)."""

    def make_fixture(self, **room_kwargs):
        guest_role, _ = Role.objects.get_or_create(name='guest')
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.guest = User.objects.create_user(email='mr-guest@example.com', password='test')
        UserRole.objects.create(user=self.guest, role=guest_role)
        self.owner = User.objects.create_user(email='mr-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)

        property_type = PropertyType.objects.create(name='Multi-room Pricing Type')
        self.property = Property.objects.create(
            owner=self.owner, property_type=property_type, name='Pricing Hotel',
            city='Galle', district='Galle', province='Southern', status='approved'
        )
        room_defaults = dict(max_adults=2, max_children=0, total_occupancy=2, total_rooms=5)
        room_defaults.update(room_kwargs)
        self.room_type = RoomType.objects.create(property=self.property, name='Deluxe', **room_defaults)
        self.pricing = Pricing.objects.create(
            room_type=self.room_type, base_price=Decimal('10000.00'),
            service_fee_percent=Decimal('5.0'), tax_percent=Decimal('10.0')
        )

    def book(self, check_in, nights, num_rooms, num_adults=1, num_children=0):
        return BookingService.create_booking(
            room_type=self.room_type, guest=self.guest,
            check_in=check_in, check_out=check_in + timedelta(days=nights),
            num_adults=num_adults, num_children=num_children, num_rooms=num_rooms
        )


class MultiRoomPricingTestCase(MultiRoomTestMixin, TestCase):
    """Regression: the stored booking price must cover every booked room."""

    def setUp(self):
        self.make_fixture()
        self.monday = _next_weekday(0)

    def test_one_room_two_nights(self):
        booking = self.book(self.monday, nights=2, num_rooms=1)
        self.assertEqual(booking.room_price, Decimal('10000.00'))
        self.assertEqual(booking.subtotal, Decimal('20000.00'))
        # 20,000 + 5% service fee = 21,000; + 10% tax = 23,100 (unchanged single-room behavior)
        self.assertEqual(booking.total_price, Decimal('23100.00'))

    def test_two_rooms_two_nights(self):
        booking = self.book(self.monday, nights=2, num_rooms=2)
        # room_price stays per room per night - not multiplied twice
        self.assertEqual(booking.room_price, Decimal('10000.00'))
        self.assertEqual(booking.subtotal, Decimal('40000.00'))
        self.assertEqual(booking.service_fee, Decimal('2000.00'))
        self.assertEqual(booking.tax, Decimal('4200.00'))
        self.assertEqual(booking.total_price, Decimal('46200.00'))

    def test_three_rooms_one_night(self):
        booking = self.book(self.monday, nights=1, num_rooms=3)
        self.assertEqual(booking.subtotal, Decimal('30000.00'))
        self.assertEqual(booking.total_price, Decimal('34650.00'))

    def test_weekend_pricing_with_multiple_rooms(self):
        self.pricing.weekend_price = Decimal('15000.00')
        self.pricing.save()
        thursday = _next_weekday(3)

        # Thursday (base 10,000) + Friday (weekend 15,000) = 25,000 per room
        booking = self.book(thursday, nights=2, num_rooms=2)
        self.assertEqual(booking.subtotal, Decimal('50000.00'))

    def test_discount_applies_to_multi_room_subtotal(self):
        breakdown = PricingCalculator(self.room_type).calculate_booking_price(
            self.monday, self.monday + timedelta(days=2), num_adults=1,
            discount_percent=Decimal('10'), num_rooms=2
        )
        self.assertEqual(breakdown['subtotal'], Decimal('40000.00'))
        self.assertEqual(breakdown['discount'], Decimal('4000.00'))

    def test_included_adults_scale_per_room(self):
        """2 adults are included per room, so 4 adults in 2 rooms pay no extra-guest fee."""
        self.pricing.extra_guest_fee = Decimal('1000.00')
        self.pricing.save()
        booking = self.book(self.monday, nights=1, num_rooms=2, num_adults=4)
        self.assertEqual(booking.subtotal, Decimal('20000.00'))

    def test_quoted_price_matches_stored_booking(self):
        client = APIClient()
        client.force_authenticate(user=self.guest)
        payload = {
            'room_type_id': str(self.room_type.id),
            'check_in_date': str(self.monday),
            'check_out_date': str(self.monday + timedelta(days=2)),
            'number_of_adults': 3,
            'number_of_rooms': 2,
        }
        quote = client.post('/api/bookings/calculate-price/', payload, format='json')
        self.assertEqual(quote.status_code, 200, quote.data)
        self.assertEqual(quote.data['data']['num_rooms'], 2)

        created = client.post('/api/bookings/', payload, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(
            Decimal(str(quote.data['data']['total'])),
            Decimal(str(created.data['data']['total_price']))
        )

    def test_check_availability_route_used_by_frontend(self):
        """lib/api.ts posts to the hyphenated check-availability URL and reads is_available."""
        self.book(self.monday, nights=2, num_rooms=3)
        client = APIClient()
        client.force_authenticate(user=self.guest)
        response = client.post('/api/bookings/check-availability/', {
            'room_type_id': str(self.room_type.id),
            'check_in_date': str(self.monday),
            'check_out_date': str(self.monday + timedelta(days=2)),
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data.get('data', response.data)
        self.assertTrue(data['is_available'])
        self.assertEqual(data['available_count'], 2)  # total_rooms=5, 3 held


class MultiRoomCapacityTestCase(MultiRoomTestMixin, TestCase):
    """Regression: guest limits apply per room, so N rooms hold N times the guests."""

    def setUp(self):
        # Per room: 2 adults, 1 child, 3 guests total
        self.make_fixture(max_adults=2, max_children=1, total_occupancy=3)
        self.check_in = _next_weekday(0)

    def test_one_room_two_adults_accepted(self):
        self.assertEqual(self.book(self.check_in, 1, num_rooms=1, num_adults=2).number_of_adults, 2)

    def test_one_room_three_adults_rejected(self):
        with self.assertRaises(ValueError):
            self.book(self.check_in, 1, num_rooms=1, num_adults=3)

    def test_two_rooms_four_adults_accepted(self):
        self.assertEqual(self.book(self.check_in, 1, num_rooms=2, num_adults=4).number_of_adults, 4)

    def test_two_rooms_five_adults_rejected(self):
        with self.assertRaises(ValueError):
            self.book(self.check_in, 1, num_rooms=2, num_adults=5)

    def test_one_room_children_within_limits_accepted(self):
        booking = self.book(self.check_in, 1, num_rooms=1, num_adults=2, num_children=1)
        self.assertEqual(booking.number_of_children, 1)

    def test_one_room_too_many_children_rejected(self):
        with self.assertRaises(ValueError):
            self.book(self.check_in, 1, num_rooms=1, num_adults=1, num_children=2)

    def test_two_rooms_children_scale_with_rooms(self):
        booking = self.book(self.check_in, 1, num_rooms=2, num_adults=4, num_children=2)
        self.assertEqual(booking.number_of_children, 2)

    def test_two_rooms_too_many_children_rejected(self):
        with self.assertRaises(ValueError):
            self.book(self.check_in, 1, num_rooms=2, num_adults=2, num_children=3)

    def test_api_accepts_four_adults_in_two_rooms(self):
        client = APIClient()
        client.force_authenticate(user=self.guest)
        response = client.post('/api/bookings/', {
            'room_type_id': str(self.room_type.id),
            'check_in_date': str(self.check_in),
            'check_out_date': str(self.check_in + timedelta(days=1)),
            'number_of_adults': 4,
            'number_of_rooms': 2,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)

    def test_api_rejects_four_adults_in_one_room(self):
        client = APIClient()
        client.force_authenticate(user=self.guest)
        response = client.post('/api/bookings/', {
            'room_type_id': str(self.room_type.id),
            'check_in_date': str(self.check_in),
            'check_out_date': str(self.check_in + timedelta(days=1)),
            'number_of_adults': 4,
            'number_of_rooms': 1,
        }, format='json')
        self.assertEqual(response.status_code, 400)


class AdminCancellationAvailabilityTestCase(MultiRoomTestMixin, TestCase):
    """Admin cancel / status changes keep the daily Availability count in sync."""

    def setUp(self):
        self.make_fixture(total_rooms=3)
        self.admin = User.objects.create_user(email='mr-admin@example.com', password='test', is_staff=True)
        self.check_in = _next_weekday(0)
        self.booking = self.book(self.check_in, nights=2, num_rooms=2)
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def daily_counts(self):
        return list(
            Availability.objects.filter(room_type=self.room_type).order_by('date').values_list('available_count', flat=True)
        )

    def test_booking_reduces_daily_count_by_room_quantity(self):
        self.assertEqual(self.daily_counts(), [1, 1])

    def test_admin_cancel_releases_daily_count(self):
        response = self.client.post(f'/api/admin/bookings/{self.booking.id}/cancel/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.daily_counts(), [3, 3])

    def test_admin_cancel_twice_does_not_double_release(self):
        self.client.post(f'/api/admin/bookings/{self.booking.id}/cancel/', {}, format='json')
        second = self.client.post(f'/api/admin/bookings/{self.booking.id}/cancel/', {}, format='json')
        self.assertEqual(second.status_code, 400)
        self.assertEqual(self.daily_counts(), [3, 3])

    def test_admin_status_change_to_cancelled_releases_daily_count(self):
        response = self.client.patch(f'/api/admin/bookings/{self.booking.id}/status/', {'status': 'cancelled'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.daily_counts(), [3, 3])

    def test_admin_status_change_to_rejected_releases_daily_count(self):
        response = self.client.patch(f'/api/admin/bookings/{self.booking.id}/status/', {'status': 'rejected'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.daily_counts(), [3, 3])

    def test_admin_confirm_keeps_rooms_held(self):
        response = self.client.patch(f'/api/admin/bookings/{self.booking.id}/status/', {'status': 'confirmed'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.daily_counts(), [1, 1])

    def test_owner_confirm_keeps_rooms_held(self):
        BookingService.owner_confirm_booking(self.booking)
        self.assertEqual(self.daily_counts(), [1, 1])

    def test_owner_reject_releases_daily_count(self):
        BookingService.owner_reject_booking(self.booking)
        self.assertEqual(self.daily_counts(), [3, 3])

    def test_guest_cancel_releases_daily_count(self):
        BookingService.cancel_booking(self.booking)
        self.assertEqual(self.daily_counts(), [3, 3])

    def test_invalid_admin_transition_changes_nothing(self):
        BookingService.cancel_booking(self.booking)
        response = self.client.patch(f'/api/admin/bookings/{self.booking.id}/status/', {'status': 'rejected'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.daily_counts(), [3, 3])


class BookingPriceIntegrityTestCase(MultiRoomTestMixin, TestCase):
    """
    SECURITY: guests must not be able to set their own discount or any other
    financial value. The stored price is always computed server-side.
    Fixture: 10,000/night, 5% service fee, 10% tax. 1 room x 2 weekday nights
    = 20,000 subtotal -> 23,100 total.
    """

    def setUp(self):
        self.make_fixture()
        self.monday = _next_weekday(0)
        self.client = APIClient()
        self.client.force_authenticate(user=self.guest)

    def post_booking(self, nights=2, **extra):
        payload = {
            'room_type_id': str(self.room_type.id),
            'check_in_date': str(self.monday),
            'check_out_date': str(self.monday + timedelta(days=nights)),
            'number_of_adults': 1,
        }
        payload.update(extra)
        response = self.client.post('/api/bookings/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return Booking.objects.get(id=response.data['data']['id'])

    def assert_full_price(self, booking, subtotal='20000.00', total='23100.00'):
        self.assertEqual(booking.discount, Decimal('0'))
        self.assertEqual(booking.subtotal, Decimal(subtotal))
        self.assertEqual(booking.total_price, Decimal(total))

    def test_guest_discount_percent_100_is_ignored(self):
        self.assert_full_price(self.post_booking(discount_percent='100'))

    def test_guest_discount_fixed_equal_to_total_is_ignored(self):
        self.assert_full_price(self.post_booking(discount_fixed='23100.00'))

    def test_guest_negative_discounts_are_ignored(self):
        self.assert_full_price(self.post_booking(discount_percent='-50', discount_fixed='-1000'))

    def test_guest_fake_totals_and_fees_are_ignored(self):
        booking = self.post_booking(
            total_price='1.00', grand_total='1.00', subtotal='1.00', discount='99999',
            room_price='1.00', tax='0', service_fee='0', number_of_nights=99,
        )
        self.assert_full_price(booking)
        self.assertEqual(booking.room_price, Decimal('10000.00'))
        self.assertEqual(booking.service_fee, Decimal('1000.00'))
        self.assertEqual(booking.tax, Decimal('2100.00'))
        self.assertEqual(booking.number_of_nights, 2)

    def test_guest_cannot_set_status_or_payment_status_on_create(self):
        booking = self.post_booking(status='confirmed', payment_status='paid')
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.payment_status, 'pending')

    def test_normal_booking_price_unchanged(self):
        self.assert_full_price(self.post_booking())

    def test_multi_room_price_with_attempted_discount(self):
        booking = self.post_booking(number_of_rooms=2, discount_percent='100')
        self.assert_full_price(booking, subtotal='40000.00', total='46200.00')

    def test_weekend_price_with_attempted_discount(self):
        self.pricing.weekend_price = Decimal('15000.00')
        self.pricing.save()
        self.monday = _next_weekday(3)  # Thursday (base) + Friday (weekend)
        booking = self.post_booking(discount_fixed='25000')
        self.assert_full_price(booking, subtotal='25000.00', total='28875.00')

    def test_quote_endpoint_ignores_guest_discount(self):
        response = self.client.post('/api/bookings/calculate-price/', {
            'room_type_id': str(self.room_type.id),
            'check_in_date': str(self.monday),
            'check_out_date': str(self.monday + timedelta(days=2)),
            'number_of_adults': 1,
            'discount_percent': '100',
            'discount_fixed': '5000',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Decimal(str(response.data['data']['discount'])), Decimal('0'))
        self.assertEqual(Decimal(str(response.data['data']['total'])), Decimal('23100.00'))

    def test_room_quote_endpoint_ignores_guest_discount(self):
        response = self.client.get(
            f'/api/properties/rooms/{self.room_type.id}/calculate_price/'
            f'?check_in={self.monday}&check_out={self.monday + timedelta(days=2)}&adults=1'
            f'&discount_percent=100&discount_fixed=5000'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Decimal(str(response.data['data']['discount'])), Decimal('0'))
        self.assertEqual(Decimal(str(response.data['data']['total'])), Decimal('23100.00'))


class BookingDeleteAndIsolationTestCase(MultiRoomTestMixin, TestCase):
    """
    SECURITY: bookings are auditable records - no hard delete or generic edit
    for any role - and users can only act on bookings they are party to.
    """

    def setUp(self):
        self.make_fixture()  # self.guest books at self.owner's property
        guest_role = Role.objects.get(name='guest')
        owner_role = Role.objects.get(name='property_owner')
        self.other_guest = User.objects.create_user(email='iso-guest-b@example.com', password='test')
        UserRole.objects.create(user=self.other_guest, role=guest_role)
        self.other_owner = User.objects.create_user(email='iso-owner-b@example.com', password='test')
        UserRole.objects.create(user=self.other_owner, role=owner_role)
        self.admin = User.objects.create_user(email='iso-admin@example.com', password='test', is_staff=True)

        self.booking = self.book(_next_weekday(0), nights=2, num_rooms=1)
        self.client = APIClient()

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return self.client

    def assert_booking_intact(self, status='pending'):
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, status)
        self.assertEqual(self.booking.total_price, Decimal('23100.00'))

    # ---- Hard delete / generic edit ----

    def test_guest_cannot_delete_own_booking(self):
        response = self.as_user(self.guest).delete(f'/api/bookings/{self.booking.id}/')
        self.assertEqual(response.status_code, 405)
        self.assert_booking_intact()

    def test_owner_cannot_delete_booking(self):
        response = self.as_user(self.owner).delete(f'/api/bookings/{self.booking.id}/')
        self.assertEqual(response.status_code, 405)
        self.assert_booking_intact()

    def test_admin_cannot_delete_booking_via_api(self):
        response = self.as_user(self.admin).delete(f'/api/bookings/{self.booking.id}/')
        self.assertEqual(response.status_code, 405)
        self.assert_booking_intact()

    def test_admin_booking_api_has_no_delete(self):
        response = self.as_user(self.admin).delete(f'/api/admin/bookings/{self.booking.id}/')
        self.assertEqual(response.status_code, 405)
        self.assert_booking_intact()

    def test_guest_cannot_patch_or_put_booking(self):
        client = self.as_user(self.guest)
        patch = client.patch(f'/api/bookings/{self.booking.id}/', {'total_price': '1.00', 'status': 'confirmed'}, format='json')
        put = client.put(f'/api/bookings/{self.booking.id}/', {'total_price': '1.00'}, format='json')
        self.assertEqual(patch.status_code, 405)
        self.assertEqual(put.status_code, 405)
        self.assert_booking_intact()

    # ---- Cancellation workflow still works (status change, row kept) ----

    def test_guest_cancellation_still_works_and_keeps_row(self):
        response = self.as_user(self.guest).post(f'/api/bookings/{self.booking.id}/cancel/', {'reason': 'Plans changed'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assert_booking_intact(status='cancelled')

    def test_owner_reject_still_works_and_keeps_row(self):
        response = self.as_user(self.owner).post(f'/api/bookings/{self.booking.id}/reject/', {'reason': 'Full'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assert_booking_intact(status='rejected')

    def test_owner_confirm_still_works(self):
        response = self.as_user(self.owner).post(f'/api/bookings/{self.booking.id}/confirm/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assert_booking_intact(status='confirmed')

    # ---- Isolation ----

    def test_other_guest_cannot_view_booking(self):
        response = self.as_user(self.other_guest).get(f'/api/bookings/{self.booking.id}/')
        self.assertEqual(response.status_code, 403)

    def test_other_guest_cannot_cancel_booking(self):
        response = self.as_user(self.other_guest).post(f'/api/bookings/{self.booking.id}/cancel/', {}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assert_booking_intact()

    def test_other_guest_does_not_see_booking_in_list(self):
        response = self.as_user(self.other_guest).get('/api/bookings/')
        results = response.data.get('results', response.data)
        self.assertNotIn(str(self.booking.id), [str(item['id']) for item in results])

    def test_other_owner_cannot_view_confirm_reject_or_cancel(self):
        client = self.as_user(self.other_owner)
        self.assertEqual(client.get(f'/api/bookings/{self.booking.id}/').status_code, 403)
        self.assertEqual(client.post(f'/api/bookings/{self.booking.id}/confirm/').status_code, 403)
        self.assertEqual(client.post(f'/api/bookings/{self.booking.id}/reject/', {}, format='json').status_code, 403)
        self.assertEqual(client.post(f'/api/bookings/{self.booking.id}/cancel/', {}, format='json').status_code, 403)
        self.assert_booking_intact()

    def test_other_owner_does_not_see_booking_in_list(self):
        response = self.as_user(self.other_owner).get('/api/bookings/')
        results = response.data.get('results', response.data)
        self.assertNotIn(str(self.booking.id), [str(item['id']) for item in results])

    def test_owner_sees_booking_for_own_property(self):
        response = self.as_user(self.owner).get(f'/api/bookings/{self.booking.id}/')
        self.assertEqual(response.status_code, 200)

    def test_admin_can_view_and_cancel_any_booking(self):
        client = self.as_user(self.admin)
        self.assertEqual(client.get(f'/api/bookings/{self.booking.id}/').status_code, 200)
        response = client.post(f'/api/admin/bookings/{self.booking.id}/cancel/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assert_booking_intact(status='cancelled')

    # ---- Payment confirmation (financial state) ----

    def test_guest_cannot_confirm_payment_on_own_booking(self):
        response = self.as_user(self.guest).post(f'/api/bookings/{self.booking.id}/confirm_payment/', {}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assert_booking_intact()

    def test_owner_cannot_confirm_payment_on_cancelled_booking(self):
        BookingService.cancel_booking(self.booking)
        response = self.as_user(self.owner).post(f'/api/bookings/{self.booking.id}/confirm_payment/', {}, format='json')
        self.assertEqual(response.status_code, 409)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')
        self.assertEqual(self.booking.payment_status, 'pending')

    def test_owner_can_confirm_payment_on_pending_booking(self):
        response = self.as_user(self.owner).post(f'/api/bookings/{self.booking.id}/confirm_payment/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.payment_status, 'paid')

    def make_payment(self):
        from apps.payments.models import Payment
        return Payment.objects.create(
            booking=self.booking, amount=self.booking.total_price, status='pending',
            payment_method='pay_at_property', gateway_name='pay_at_property'
        )

    def test_guest_cannot_confirm_own_payment_record(self):
        payment = self.make_payment()
        response = self.as_user(self.guest).post(
            f'/api/payments/{payment.id}/confirm/', {'status': 'paid', 'transaction_reference': 'TXN-1'}, format='json'
        )
        self.assertEqual(response.status_code, 403)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'pending')
        self.assert_booking_intact()

    def test_payment_confirm_cannot_resurrect_cancelled_booking(self):
        payment = self.make_payment()
        BookingService.cancel_booking(self.booking)
        response = self.as_user(self.owner).post(
            f'/api/payments/{payment.id}/confirm/', {'status': 'paid', 'transaction_reference': 'TXN-1'}, format='json'
        )
        self.assertEqual(response.status_code, 409)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'pending')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')
