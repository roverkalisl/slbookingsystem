"""
Tests for the guest reviews API.

Run with: python manage.py test apps.reviews
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.bookings.models import Booking
from apps.bookings.service import BookingService
from apps.core.models import Role, UserRole
from apps.properties.models import Property, PropertyType, RoomType, Pricing
from .models import Review

User = get_user_model()


class ReviewApiTestCase(TestCase):
    def setUp(self):
        guest_role, _ = Role.objects.get_or_create(name='guest')
        owner_role, _ = Role.objects.get_or_create(name='property_owner')

        self.guest = User.objects.create_user(email='guest@example.com', password='test')
        UserRole.objects.create(user=self.guest, role=guest_role)

        self.other_guest = User.objects.create_user(email='other@example.com', password='test')
        UserRole.objects.create(user=self.other_guest, role=guest_role)

        self.owner = User.objects.create_user(email='owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)

        property_type = PropertyType.objects.create(name='Villa')
        self.property = Property.objects.create(
            owner=self.owner, property_type=property_type, name='Test Villa',
            city='Colombo', district='Western', province='Western', status='approved'
        )
        self.room_type = RoomType.objects.create(
            property=self.property, name='Room', max_adults=2, total_occupancy=2, total_rooms=1
        )
        Pricing.objects.create(room_type=self.room_type, base_price=Decimal('5000.00'))

        check_in = date.today() + timedelta(days=10)
        check_out = check_in + timedelta(days=2)
        self.booking = BookingService.create_booking(
            room_type=self.room_type, guest=self.guest, check_in=check_in, check_out=check_out, num_adults=2
        )
        BookingService.owner_confirm_booking(self.booking)

        self.pending_booking = BookingService.create_booking(
            room_type=self.room_type, guest=self.guest,
            check_in=check_in + timedelta(days=30), check_out=check_in + timedelta(days=32), num_adults=2
        )

    def test_guest_can_review_own_confirmed_booking(self):
        client = APIClient()
        client.force_authenticate(user=self.guest)
        response = client.post('/api/reviews/', {
            'booking_id': str(self.booking.id),
            'rating': 5,
            'title': 'Great stay',
            'comment': 'Loved it here.',
        }, format='json')

        self.assertEqual(response.status_code, 201, response.content)
        review = Review.objects.get(booking=self.booking)
        self.assertEqual(review.overall_rating, 5)
        self.assertEqual(review.property, self.property)
        self.assertIn('Great stay', review.comment)

    def test_cannot_review_pending_booking(self):
        """Spec: only an eligible (confirmed) booking can be reviewed"""
        client = APIClient()
        client.force_authenticate(user=self.guest)
        response = client.post('/api/reviews/', {
            'booking_id': str(self.pending_booking.id),
            'rating': 4,
        }, format='json')

        self.assertEqual(response.status_code, 400)

    def test_cannot_review_someone_elses_booking(self):
        """Object-level security: guest cannot review a booking that isn't theirs"""
        client = APIClient()
        client.force_authenticate(user=self.other_guest)
        response = client.post('/api/reviews/', {
            'booking_id': str(self.booking.id),
            'rating': 1,
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Review.objects.filter(booking=self.booking).exists())

    def test_cannot_review_same_booking_twice(self):
        client = APIClient()
        client.force_authenticate(user=self.guest)
        first = client.post('/api/reviews/', {'booking_id': str(self.booking.id), 'rating': 5}, format='json')
        self.assertEqual(first.status_code, 201)

        second = client.post('/api/reviews/', {'booking_id': str(self.booking.id), 'rating': 3}, format='json')
        self.assertIn(second.status_code, (400, 409))
        self.assertEqual(Review.objects.filter(booking=self.booking).count(), 1)

    def test_reviews_are_publicly_listable_by_property(self):
        Review.objects.create(
            booking=self.booking, property=self.property, guest=self.guest,
            overall_rating=4, comment='Nice place'
        )

        client = APIClient()  # no auth - guests browsing should see reviews
        response = client.get(f'/api/reviews/?property_id={self.property.id}')

        self.assertEqual(response.status_code, 200)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 1)

    def test_owner_can_respond_to_review(self):
        review = Review.objects.create(
            booking=self.booking, property=self.property, guest=self.guest,
            overall_rating=4, comment='Nice place'
        )

        client = APIClient()
        client.force_authenticate(user=self.owner)
        response = client.post(f'/api/reviews/{review.id}/response/', {'response_text': 'Thank you!'}, format='json')

        self.assertEqual(response.status_code, 201, response.content)

    def test_stranger_cannot_respond_to_review(self):
        """Object-level security: only the property's own owner can respond"""
        review = Review.objects.create(
            booking=self.booking, property=self.property, guest=self.guest,
            overall_rating=4, comment='Nice place'
        )

        client = APIClient()
        client.force_authenticate(user=self.other_guest)
        response = client.post(f'/api/reviews/{review.id}/response/', {'response_text': 'Not yours'}, format='json')

        self.assertEqual(response.status_code, 403)
