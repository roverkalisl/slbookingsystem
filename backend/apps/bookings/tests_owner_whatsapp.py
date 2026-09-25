"""
Guest -> owner WhatsApp contact on bookings.

The owner's number is resolved live (Booking -> Property -> PropertyContact
WhatsApp, else the owner's phone), normalised to wa.me digits, and exposed
ONLY to the booking's own guest (or an admin).

Run with: python manage.py test apps.bookings.tests_owner_whatsapp
"""

from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from apps.core.models import Role, UserRole
from apps.notifications.whatsapp import (
    booking_inquiry_message, normalize_whatsapp_number, owner_whatsapp_number, whatsapp_url,
)
from apps.properties.models import Property, PropertyContact, PropertyType, RoomType
from .models import Booking

User = get_user_model()
BOOKINGS_URL = '/api/bookings/'


class NormalizeWhatsAppNumberTestCase(SimpleTestCase):
    def test_sri_lankan_and_international_formats(self):
        for raw in ['0771234567', '077 123 4567', '+94 77 123 4567', '+94-77-123-4567',
                    '94771234567', '0094771234567', '771234567']:
            self.assertEqual(normalize_whatsapp_number(raw), '94771234567', raw)
        self.assertEqual(normalize_whatsapp_number('+44 20 7946 0958'), '442079460958')

    def test_invalid_or_missing_numbers(self):
        for raw in [None, '', '   ', 'abc', '123', '+1234567890123456789', '+0771234567']:
            self.assertIsNone(normalize_whatsapp_number(raw), raw)

    def test_url_encodes_the_message(self):
        url = whatsapp_url('94771234567', 'Hello & welcome?\nLine 2 #1')
        self.assertTrue(url.startswith('https://wa.me/94771234567?text='))
        self.assertNotIn(' ', url)
        self.assertNotIn('\n', url)
        self.assertEqual(parse_qs(urlparse(url).query)['text'][0], 'Hello & welcome?\nLine 2 #1')
        self.assertIsNone(whatsapp_url(None, 'x'))


class OwnerWhatsAppOnBookingsTestCase(APITestCase):
    def setUp(self):
        guest_role, _ = Role.objects.get_or_create(name='guest')
        owner_role, _ = Role.objects.get_or_create(name='property_owner')

        self.owner = User.objects.create_user(email='wa-owner@example.com', password='x', phone='077 123 4567')
        self.other_owner = User.objects.create_user(email='wa-other-owner@example.com', password='x',
                                                    phone='+94 71 999 8888')
        self.guest = User.objects.create_user(email='wa-guest@example.com', password='x')
        self.other_guest = User.objects.create_user(email='wa-other-guest@example.com', password='x')
        self.admin = User.objects.create_user(email='wa-admin@example.com', password='x', is_staff=True)
        for user in (self.owner, self.other_owner):
            UserRole.objects.create(user=user, role=owner_role)
        for user in (self.guest, self.other_guest):
            UserRole.objects.create(user=user, role=guest_role)

        villa = PropertyType.objects.create(name='WA Villa Type')
        self.prop = self.make_property(self.owner, 'Lake View Villa', villa)
        self.other_prop = self.make_property(self.other_owner, 'Hill Top Villa', villa)
        self.booking = self.make_booking(self.prop, self.guest, 'SLB-WA-0001')
        self.other_booking = self.make_booking(self.other_prop, self.other_guest, 'SLB-WA-0002')

    @staticmethod
    def make_property(owner, name, property_type):
        prop = Property.objects.create(owner=owner, property_type=property_type, name=name, description='d',
                                       city='Kandy', district='Kandy', province='Central', status='approved')
        RoomType.objects.create(property=prop, name='Room', max_adults=2, total_occupancy=3, total_rooms=1)
        return prop

    @staticmethod
    def make_booking(prop, guest, reference):
        check_in = date.today() + timedelta(days=10)
        return Booking.objects.create(
            booking_reference=reference, property=prop, room_type=prop.room_types.first(), guest=guest,
            check_in_date=check_in, check_out_date=check_in + timedelta(days=2), number_of_nights=2,
            number_of_adults=2, number_of_children=1,
            room_price=Decimal('10000'), subtotal=Decimal('20000'), total_price=Decimal('20000'),
        )

    def detail(self, booking):
        response = self.client.get(f'{BOOKINGS_URL}{booking.id}/')
        return response, response.data.get('data', response.data) if hasattr(response, 'data') else None

    def listed(self):
        data = self.client.get(BOOKINGS_URL).data
        return data.get('results', data) if isinstance(data, dict) else data

    # --- resolution ---

    def test_booking_resolves_its_own_property_owner(self):
        self.assertEqual(self.booking.property.owner, self.owner)
        self.assertEqual(owner_whatsapp_number(self.booking.property), '94771234567')
        self.assertEqual(owner_whatsapp_number(self.other_booking.property), '94719998888')

    def test_property_whatsapp_contact_takes_precedence_over_owner_phone(self):
        contact = PropertyContact.objects.create(property=self.prop, whatsapp_number='+94 76 555 4444')
        contact.refresh_from_db()
        self.assertEqual(contact.whatsapp_number, '94765554444')  # stored normalised
        self.prop.refresh_from_db()
        self.assertEqual(owner_whatsapp_number(self.prop), '94765554444')

    def test_invalid_property_contact_falls_back_to_owner_phone(self):
        PropertyContact.objects.create(property=self.prop, whatsapp_number='n/a')
        self.prop.refresh_from_db()
        self.assertEqual(owner_whatsapp_number(self.prop), '94771234567')

    # --- API exposure ---

    def test_guest_gets_owner_whatsapp_on_booking_detail(self):
        self.client.force_authenticate(self.guest)
        response, data = self.detail(self.booking)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['owner_whatsapp_number'], '94771234567')
        url = data['owner_whatsapp_url']
        self.assertTrue(url.startswith('https://wa.me/94771234567?text='))
        self.assertEqual(parse_qs(urlparse(url).query)['text'][0], booking_inquiry_message(self.booking))

    def test_guest_gets_owner_whatsapp_in_my_bookings_list(self):
        self.client.force_authenticate(self.guest)
        rows = self.listed()
        self.assertEqual([row['booking_reference'] for row in rows], ['SLB-WA-0001'])
        self.assertEqual(rows[0]['owner_whatsapp_number'], '94771234567')
        self.assertTrue(rows[0]['owner_whatsapp_url'].startswith('https://wa.me/94771234567?text='))

    def test_missing_whatsapp_number_is_null_not_an_error(self):
        User.objects.filter(pk=self.owner.pk).update(phone=None)
        self.client.force_authenticate(self.guest)
        response, data = self.detail(self.booking)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(data['owner_whatsapp_number'])
        self.assertIsNone(data['owner_whatsapp_url'])

    def test_guest_cannot_get_another_propertys_owner_contact(self):
        self.client.force_authenticate(self.guest)
        response, _ = self.detail(self.other_booking)
        self.assertIn(response.status_code, (403, 404))
        self.assertNotIn('94719998888', str(response.content))
        self.assertNotIn('94719998888', str(self.client.get(BOOKINGS_URL).content))

    def test_owner_does_not_receive_owner_contact_fields(self):
        """The owner sees their own property's booking, but the guest->owner contact is for guests."""
        self.client.force_authenticate(self.owner)
        response, data = self.detail(self.booking)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(data['owner_whatsapp_number'])
        self.assertIsNone(data['owner_whatsapp_url'])

    def test_owner_cannot_open_another_owners_booking(self):
        self.client.force_authenticate(self.owner)
        response, _ = self.detail(self.other_booking)
        self.assertIn(response.status_code, (403, 404))
        self.assertNotIn('94719998888', str(response.content))

    def test_admin_can_see_owner_contact(self):
        self.client.force_authenticate(self.admin)
        _, data = self.detail(self.booking)
        self.assertEqual(data['owner_whatsapp_number'], '94771234567')

    def test_anonymous_gets_no_booking_data(self):
        response = self.client.get(f'{BOOKINGS_URL}{self.booking.id}/')
        self.assertIn(response.status_code, (401, 403))

    # --- message ---

    def test_booking_message_content(self):
        message = booking_inquiry_message(self.booking)
        check_in = self.booking.check_in_date.isoformat()
        check_out = self.booking.check_out_date.isoformat()
        self.assertEqual(message, (
            'Hello, I have a booking inquiry.\n\n'
            'Property: Lake View Villa\n'
            'Booking Reference: SLB-WA-0001\n'
            f'Check-in: {check_in}\n'
            f'Check-out: {check_out}\n'
            'Guests: 3\n\n'
            'I would like to discuss/confirm my booking.'
        ))
