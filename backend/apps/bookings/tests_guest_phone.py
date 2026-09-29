"""
Tests for the guest WhatsApp / mobile number on bookings:
validation + normalisation, storage on the primary BookingGuest, backward
compatibility with bookings that have no number, and who can read it back.

Run with: python manage.py test apps.bookings.tests_guest_phone
"""

from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from apps.core.models import Role, UserRole
from apps.notifications.whatsapp import normalize_phone_e164, normalize_whatsapp_number, whatsapp_url
from apps.properties.models import Property, PropertyType, RoomType, Pricing
from .models import Booking, BookingGuest
from .serializers import BookingCreateSerializer, BookingGuestSerializer
from .service import BookingService

User = get_user_model()


class NormalizePhoneTestCase(SimpleTestCase):
    def test_valid_numbers_are_normalised_to_e164(self):
        for raw in ['0771234567', '771234567', '+94771234567', '+94 77 123 4567',
                    '0094771234567', '077-123-4567', ' (077) 123 4567 ']:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_phone_e164(raw), '+94771234567')

    def test_foreign_international_number_is_kept(self):
        self.assertEqual(normalize_phone_e164('+44 7911 123456'), '+447911123456')

    def test_invalid_numbers_are_rejected(self):
        for raw in [None, '', '   ', 'abc', '123', '+0771234567', '+1234567890123456', 'phone: n/a']:
            with self.subTest(raw=raw):
                self.assertIsNone(normalize_phone_e164(raw))

    def test_whatsapp_link_from_stored_number(self):
        message = 'Hello Nimal, this is Sea Villa regarding your SL Booking reservation BK123.'
        url = whatsapp_url(normalize_whatsapp_number('+94771234567'), message)
        self.assertEqual(url, f'https://wa.me/94771234567?text={quote(message, safe="")}')
        self.assertIsNone(whatsapp_url(normalize_whatsapp_number('not a number'), message))


class GuestPhoneSerializerTestCase(SimpleTestCase):
    def test_guest_phone_is_required(self):
        serializer = BookingCreateSerializer(data={})
        serializer.is_valid()
        self.assertIn('guest_phone', serializer.errors)
        self.assertEqual(str(serializer.errors['guest_phone'][0]), 'WhatsApp / mobile number is required.')

    def test_guest_detail_phone_is_optional_but_validated(self):
        blank = BookingGuestSerializer(data={'first_name': 'A', 'last_name': 'B', 'email': 'a@example.com', 'phone': ''})
        self.assertTrue(blank.is_valid(), blank.errors)
        good = BookingGuestSerializer(data={'first_name': 'A', 'last_name': 'B', 'email': 'a@example.com', 'phone': '0771234567'})
        self.assertTrue(good.is_valid(), good.errors)
        self.assertEqual(good.validated_data['phone'], '+94771234567')
        bad = BookingGuestSerializer(data={'first_name': 'A', 'last_name': 'B', 'email': 'a@example.com', 'phone': '12ab'})
        self.assertFalse(bad.is_valid())
        self.assertIn('phone', bad.errors)


class GuestPhoneBookingApiTestCase(APITestCase):
    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.owner_a = User.objects.create_user(email='gp-owner-a@example.com', password='test')
        UserRole.objects.create(user=self.owner_a, role=owner_role)
        self.owner_b = User.objects.create_user(email='gp-owner-b@example.com', password='test')
        UserRole.objects.create(user=self.owner_b, role=owner_role)
        self.guest = User.objects.create_user(
            email='gp-guest@example.com', password='test', first_name='Nimal', last_name='Perera'
        )
        UserRole.objects.create(user=self.guest, role=guest_role)
        self.admin = User.objects.create_user(email='gp-admin@example.com', password='test', is_staff=True)

        property_type = PropertyType.objects.create(name='Guest Phone Villa Type')
        self.property_a = Property.objects.create(
            owner=self.owner_a, property_type=property_type, name='Sea Villa',
            city='Galle', district='Galle', province='Southern', status='approved'
        )
        self.room_a = RoomType.objects.create(
            property=self.property_a, name='Room', max_adults=2, total_occupancy=2, total_rooms=3
        )
        Pricing.objects.create(room_type=self.room_a, base_price=Decimal('5000.00'))

        property_b = Property.objects.create(
            owner=self.owner_b, property_type=property_type, name='Hill Villa',
            city='Ella', district='Badulla', province='Uva', status='approved'
        )
        self.room_b = RoomType.objects.create(
            property=property_b, name='Room', max_adults=2, total_occupancy=2, total_rooms=3
        )
        Pricing.objects.create(room_type=self.room_b, base_price=Decimal('5000.00'))

        self.check_in = date.today() + timedelta(days=10)
        self.check_out = self.check_in + timedelta(days=2)

    def payload(self, room=None, **overrides):
        data = {
            'room_type_id': str((room or self.room_a).id),
            'check_in_date': str(self.check_in),
            'check_out_date': str(self.check_out),
            'number_of_adults': 2,
            'guest_phone': '077 123 4567',
        }
        data.update(overrides)
        return data

    def book(self, **overrides):
        self.client.force_authenticate(self.guest)
        return self.client.post('/api/bookings/', self.payload(**overrides), format='json')

    def list_bookings(self, user):
        self.client.force_authenticate(user)
        data = self.client.get('/api/bookings/').data
        return data.get('results', data) if isinstance(data, dict) else data

    def detail(self, user, booking):
        self.client.force_authenticate(user)
        return self.client.get(f'/api/bookings/{booking.id}/')

    # --- creation ---

    def test_booking_stores_normalised_phone_on_primary_guest(self):
        response = self.book()
        self.assertEqual(response.status_code, 201, response.data)
        booking = Booking.objects.get(id=response.data['data']['id'])
        primary = booking.guests.get(is_primary_guest=True)
        self.assertEqual(primary.phone, '+94771234567')
        self.assertEqual(primary.email, 'gp-guest@example.com')

    def test_phone_does_not_change_status_or_price(self):
        with_phone = Booking.objects.get(id=self.book().data['data']['id'])
        without_phone = BookingService.create_booking(
            room_type=self.room_a, guest=self.guest,
            check_in=self.check_in, check_out=self.check_out, num_adults=2,
        )
        self.assertEqual(with_phone.status, without_phone.status)
        self.assertEqual(with_phone.payment_status, without_phone.payment_status)
        self.assertEqual(with_phone.total_price, without_phone.total_price)

    def test_missing_phone_is_rejected_and_no_booking_created(self):
        payload = self.payload()
        del payload['guest_phone']
        self.client.force_authenticate(self.guest)
        response = self.client.post('/api/bookings/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('guest_phone', str(response.data))
        self.assertEqual(Booking.objects.count(), 0)

    def test_invalid_phone_is_rejected_and_no_booking_created(self):
        for raw in ['', '12345', 'call me', '+0771234567']:
            with self.subTest(raw=raw):
                response = self.book(guest_phone=raw)
                self.assertEqual(response.status_code, 400)
                self.assertIn('guest_phone', str(response.data))
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(BookingGuest.objects.count(), 0)

    def test_explicit_guest_details_phone_wins_and_is_normalised(self):
        response = self.book(guests=[{
            'first_name': 'Kamal', 'last_name': 'Silva', 'email': 'kamal@example.com',
            'phone': '0712345678', 'is_primary_guest': True,
        }])
        self.assertEqual(response.status_code, 201, response.data)
        primary = Booking.objects.get(id=response.data['data']['id']).guests.get(is_primary_guest=True)
        self.assertEqual(primary.phone, '+94712345678')

    def test_guest_details_without_phone_fall_back_to_guest_phone(self):
        response = self.book(guests=[{
            'first_name': 'Kamal', 'last_name': 'Silva', 'email': 'kamal@example.com', 'is_primary_guest': True,
        }])
        self.assertEqual(response.status_code, 201, response.data)
        primary = Booking.objects.get(id=response.data['data']['id']).guests.get(is_primary_guest=True)
        self.assertEqual(primary.phone, '+94771234567')

    # --- backward compatibility ---

    def test_existing_booking_without_phone_still_works(self):
        booking = BookingService.create_booking(
            room_type=self.room_a, guest=self.guest,
            check_in=self.check_in, check_out=self.check_out, num_adults=2,
        )
        self.assertEqual(booking.guests.get(is_primary_guest=True).phone, '')

        rows = self.list_bookings(self.owner_a)
        row = next(r for r in rows if r['id'] == str(booking.id))
        self.assertIn(row['guest_phone'], (None, ''))
        self.assertEqual(row['guest_email'], 'gp-guest@example.com')  # Email Guest still works
        self.assertEqual(self.detail(self.owner_a, booking).status_code, 200)
        self.assertEqual(self.detail(self.guest, booking).status_code, 200)

    # --- who can read the number ---

    def test_owner_sees_phone_for_own_property_booking(self):
        booking_id = self.book().data['data']['id']
        row = next(r for r in self.list_bookings(self.owner_a) if r['id'] == booking_id)
        self.assertEqual(row['guest_phone'], '+94771234567')
        self.assertEqual(row['guest_email'], 'gp-guest@example.com')

        booking = Booking.objects.get(id=booking_id)
        guests = self.detail(self.owner_a, booking).data['data']['guests']
        self.assertEqual(guests[0]['phone'], '+94771234567')

    def test_other_owner_cannot_see_guest_phone(self):
        booking_id = self.book().data['data']['id']
        booking = Booking.objects.get(id=booking_id)

        rows = self.list_bookings(self.owner_b)
        self.assertNotIn(booking_id, [r['id'] for r in rows])
        self.assertNotIn('+94771234567', str(rows))

        response = self.detail(self.owner_b, booking)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('+94771234567', str(response.data))

    def test_guest_sees_own_phone_and_admin_can_view(self):
        booking_id = self.book().data['data']['id']
        booking = Booking.objects.get(id=booking_id)

        guest_detail = self.detail(self.guest, booking).data['data']
        self.assertEqual(guest_detail['guests'][0]['phone'], '+94771234567')
        row = next(r for r in self.list_bookings(self.guest) if r['id'] == booking_id)
        self.assertEqual(row['guest_phone'], '+94771234567')

        admin_detail = self.detail(self.admin, booking).data['data']
        self.assertEqual(admin_detail['guests'][0]['phone'], '+94771234567')

    def test_public_property_api_never_exposes_guest_phone(self):
        self.book()
        self.client.force_authenticate(None)
        for url in [f'/api/properties/{self.property_a.id}/', '/api/properties/']:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn('771234567', str(response.data))
