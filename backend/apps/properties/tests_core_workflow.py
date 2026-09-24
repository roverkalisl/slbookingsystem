"""
End-to-end API test of the core SL Booking workflow, using the same endpoints
and payload shapes as the frontend pages:

OWNER add property -> photos -> room -> room photos -> pricing -> availability
-> submit -> ADMIN review/approve -> GUEST search/view/price/availability/book

This exercises the backend contract the UI depends on. It does not drive a
browser - frontend pages are verified by type-check/build and code review.

Run with: python manage.py test apps.properties.tests_core_workflow
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.core.models import Role, UserRole
from .models import Amenity, Property, PropertyType, RoomType, Pricing

User = get_user_model()


def next_monday(min_days_ahead=21):
    start = date.today() + timedelta(days=min_days_ahead)
    return start + timedelta(days=(0 - start.weekday()) % 7)


class CoreWorkflowEndToEndTestCase(APITestCase):
    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.owner = User.objects.create_user(email='flow-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.other_owner = User.objects.create_user(email='flow-owner-b@example.com', password='test')
        UserRole.objects.create(user=self.other_owner, role=owner_role)
        self.guest = User.objects.create_user(email='flow-guest@example.com', password='test')
        UserRole.objects.create(user=self.guest, role=guest_role)
        self.guest2 = User.objects.create_user(email='flow-guest2@example.com', password='test')
        UserRole.objects.create(user=self.guest2, role=guest_role)
        self.admin = User.objects.create_user(email='flow-admin@example.com', password='test', is_staff=True)

        # Master data as seeded by seed_master_data - ids are whatever the DB assigns
        PropertyType.objects.create(name='Flow Guest House')
        self.villa_type = PropertyType.objects.create(name='Flow Villa')
        Amenity.objects.create(name='Flow WiFi', slug='flow-wifi')
        Amenity.objects.create(name='Flow Pool', slug='flow-pool')

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return self.client

    def photo(self, label):
        return {'cloudinary_url': f'https://res.cloudinary.com/demo/{label}.jpg', 'cloudinary_public_id': label}

    def test_full_owner_admin_guest_workflow(self):
        owner = self.as_user(self.owner)

        # --- Master data comes from the backend (no hardcoded ids) ---
        types = owner.get('/api/properties/types/').data
        types = types.get('results', types) if isinstance(types, dict) else types
        amenities = owner.get('/api/properties/amenities/').data
        amenities = amenities.get('results', amenities) if isinstance(amenities, dict) else amenities
        villa_id = next(t['id'] for t in types if t['name'] == 'Flow Villa')
        amenity_ids = [a['id'] for a in amenities if a['name'] in ('Flow WiFi', 'Flow Pool')]
        self.assertEqual(villa_id, self.villa_type.id)
        self.assertEqual(len(amenity_ids), 2)

        # --- 1. Create property as draft (add page payload) ---
        response = owner.post('/api/properties/', {
            'name': 'Flow Villa Ella', 'property_type': villa_id,
            'description': 'Hill-country villa', 'address': '12 Tea Estate Road',
            'city': 'Ella', 'district': 'Badulla', 'province': 'Uva',
            'latitude': '6.86660000', 'longitude': '81.04660000',
            'google_maps_url': 'https://maps.google.com/?q=6.8666,81.0466',
            'status': 'draft', 'amenity_ids': amenity_ids,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        property_id = response.data.get('data', response.data)['id']
        prop = Property.objects.get(id=property_id)
        self.assertEqual(prop.status, 'draft')
        self.assertEqual(prop.owner, self.owner)
        self.assertEqual(set(prop.amenities.values_list('id', flat=True)), set(amenity_ids))
        self.assertFalse(prop.room_types.exists())  # no automatic rooms

        # --- 2. Property photos: 7 (more than 5) ---
        for i in range(7):
            r = owner.post(f'/api/properties/{property_id}/photos/', self.photo(f'p{i}'), format='json')
            self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(prop.photos.count(), 7)

        # Incomplete property: submit refused, stays an editable draft
        r = owner.post(f'/api/properties/{property_id}/submit-for-approval/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('Property must have at least one active room type.', r.data['errors'])
        r = owner.patch(f'/api/properties/{property_id}/', {'short_description': 'Updated draft'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)

        # --- 3. Add room (exact add-room form payload) ---
        r = owner.post(f'/api/properties/{property_id}/rooms/', {
            'name': 'Family Suite', 'description': 'Two bedrooms', 'room_type': 'suite',
            'bed_configuration': 'king', 'bathroom_type': 'en-suite', 'room_size_sqft': 450,
            'max_adults': 4, 'max_children': 1, 'number_of_beds': 2, 'total_rooms': 3, 'view_type': '',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        room = RoomType.objects.get(id=r.data['data']['id'])
        self.assertEqual(room.property_id, prop.id)
        self.assertEqual(room.total_occupancy, 5)  # derived from 4 adults + 1 child

        # --- 4. Room photos: 6 ---
        for i in range(6):
            r = owner.post(f'/api/properties/rooms/{room.id}/add-photo/', self.photo(f'r{i}'), format='json')
            self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(room.photos.count(), 6)

        # Pricing still missing -> submit refused
        r = owner.post(f'/api/properties/{property_id}/submit-for-approval/')
        self.assertIn("Room 'Family Suite' does not have pricing configured.", r.data['errors'])

        # --- 5. Pricing (first-time create used to 500) ---
        r = owner.post(f'/api/properties/rooms/{room.id}/pricing/',
                       {'base_price': '10000.00', 'weekend_price': None}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(Pricing.objects.get(room_type=room).base_price, Decimal('10000.00'))

        # --- 6. Availability: calendar + block/unblock ---
        check_in = next_monday()
        check_out = check_in + timedelta(days=2)
        r = owner.get(f'/api/properties/rooms/{room.id}/calendar/?start_date={check_in}&end_date={check_out}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['data']['days'][0]['available_count'], 3)
        far = check_in + timedelta(days=30)
        self.assertEqual(owner.post(f'/api/properties/rooms/{room.id}/block-dates/',
                                    {'start_date': str(far), 'end_date': str(far)}, format='json').status_code, 200)
        self.assertEqual(owner.post(f'/api/properties/rooms/{room.id}/unblock-dates/',
                                    {'start_date': str(far), 'end_date': str(far)}, format='json').status_code, 200)

        # --- 7. Submit for approval ---
        r = owner.post(f'/api/properties/{property_id}/submit-for-approval/')
        self.assertEqual(r.status_code, 200, r.data)
        prop.refresh_from_db()
        self.assertEqual(prop.status, 'pending_approval')
        # Owner cannot approve their own property, nor edit it while pending
        self.assertEqual(owner.post(f'/api/properties/{property_id}/approve/').status_code, 403)
        self.assertEqual(owner.patch(f'/api/properties/{property_id}/', {'name': 'x'}, format='json').status_code, 403)

        # Not bookable/searchable before approval
        guest = self.as_user(self.guest)
        self.assertEqual(guest.get(f'/api/properties/{property_id}/').status_code, 404)

        # --- 8. Admin review + approve ---
        admin = self.as_user(self.admin)
        listing = admin.get('/api/properties/?status=pending_approval').data
        listing = listing.get('results', listing)
        self.assertIn(str(prop.id), [str(p['id']) for p in listing])
        detail = admin.get(f'/api/properties/{property_id}/').data
        detail = detail.get('data', detail)
        self.assertEqual(len(detail['photos']), 7)
        self.assertEqual(len(detail['room_types']), 1)
        self.assertEqual(len(detail['room_types'][0]['photos']), 6)
        self.assertEqual(Decimal(str(detail['room_types'][0]['pricing']['base_price'])), Decimal('10000.00'))
        self.assertEqual(admin.post(f'/api/properties/{property_id}/approve/').status_code, 200)
        prop.refresh_from_db()
        self.assertEqual(prop.status, 'approved')

        # --- 9. Guest search + property page ---
        self.client.force_authenticate(user=None)
        results = self.client.get('/api/properties/?city=Ella').data
        results = results.get('results', results)
        self.assertIn(str(prop.id), [str(p['id']) for p in results])
        r = self.client.get(f'/api/properties/search/advanced/?city=Ella&check_in={check_in}&check_out={check_out}')
        self.assertEqual(r.status_code, 200)
        advanced = r.data.get('results') or r.data.get('data') or []
        if isinstance(advanced, dict):
            advanced = advanced.get('results', [])
        self.assertIn('Flow Villa Ella', [p['name'] for p in advanced])

        page = self.client.get(f'/api/properties/{property_id}/').data
        page = page.get('data', page)
        self.assertEqual(len(page['photos']), 7)
        self.assertEqual(len(page['amenities']), 2)
        self.assertEqual(len(page['room_types'][0]['photos']), 6)
        self.assertEqual(Decimal(str(page['room_types'][0]['pricing']['base_price'])), Decimal('10000.00'))

        # --- 10. Guest price + availability + booking (2 rooms, 2 weekday nights) ---
        guest = self.as_user(self.guest)
        payload = {
            'room_type_id': str(room.id), 'check_in_date': str(check_in), 'check_out_date': str(check_out),
            'number_of_adults': 8, 'number_of_rooms': 2,
        }
        quote = guest.post('/api/bookings/calculate-price/', payload, format='json')
        self.assertEqual(quote.status_code, 200, quote.data)
        self.assertEqual(Decimal(str(quote.data['data']['room_subtotal'])), Decimal('40000.00'))
        avail = guest.post('/api/bookings/check-availability/', {
            'room_type_id': str(room.id), 'check_in_date': str(check_in), 'check_out_date': str(check_out),
        }, format='json')
        self.assertTrue(avail.data['data']['is_available'])
        self.assertEqual(avail.data['data']['available_count'], 3)

        booked = guest.post('/api/bookings/', {**payload, 'discount_percent': '100', 'total_price': '1'}, format='json')
        self.assertEqual(booked.status_code, 201, booked.data)
        booking = Booking.objects.get(id=booked.data['data']['id'])
        # 40,000 + 5% service fee + 10% tax - server-calculated, guest discount ignored
        self.assertEqual(booking.total_price, Decimal('46200.00'))
        self.assertEqual(booking.number_of_rooms, 2)

        # Only 1 room left -> a second 2-room booking is refused
        other = self.as_user(self.guest2)
        self.assertEqual(other.post('/api/bookings/', {**payload, 'number_of_adults': 2}, format='json').status_code, 409)

        # --- 11. Booking safety + owner handling ---
        self.assertEqual(self.as_user(self.guest).delete(f'/api/bookings/{booking.id}/').status_code, 405)
        self.assertEqual(self.as_user(self.owner).delete(f'/api/bookings/{booking.id}/').status_code, 405)
        self.assertEqual(self.as_user(self.owner).post(f'/api/bookings/{booking.id}/confirm/').status_code, 200)

        # --- 12. Cross-owner protection on the approved property ---
        intruder = self.as_user(self.other_owner)
        self.assertEqual(intruder.delete(f'/api/properties/rooms/{room.id}/').status_code, 403)
        self.assertEqual(intruder.post(f'/api/properties/rooms/{room.id}/add-photo/', self.photo('x'), format='json').status_code, 403)
        self.assertEqual(intruder.post(f'/api/properties/rooms/{room.id}/pricing/', {'base_price': '1'}, format='json').status_code, 403)
        self.assertTrue(RoomType.objects.filter(id=room.id).exists())


class RoomPricingEndpointTestCase(APITestCase):
    """POST /api/properties/rooms/{id}/pricing/ - used by the add-room and rooms pages."""

    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='price-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)
        prop = Property.objects.create(
            owner=self.owner, property_type=PropertyType.objects.create(name='Price Type'), name='Price Villa',
            description='d', city='Galle', district='Galle', province='Southern', status='draft',
        )
        self.room = RoomType.objects.create(property=prop, name='Room', max_adults=2, total_occupancy=2, total_rooms=1)
        self.client.force_authenticate(user=self.owner)
        self.url = f'/api/properties/rooms/{self.room.id}/pricing/'

    def test_first_time_pricing_is_created(self):
        r = self.client.post(self.url, {'base_price': '8500.00', 'weekend_price': '9500.00'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        pricing = Pricing.objects.get(room_type=self.room)
        self.assertEqual(pricing.base_price, Decimal('8500.00'))
        self.assertEqual(pricing.weekend_price, Decimal('9500.00'))

    def test_first_time_pricing_requires_base_price(self):
        r = self.client.post(self.url, {'weekend_price': '9500.00'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Pricing.objects.filter(room_type=self.room).exists())

    def test_update_keeps_unsent_fields_and_clears_weekend(self):
        self.client.post(self.url, {'base_price': '8500.00', 'weekend_price': '9500.00'}, format='json')
        self.client.post(self.url, {'base_price': '9000.00', 'weekend_price': None}, format='json')
        pricing = Pricing.objects.get(room_type=self.room)
        self.assertEqual(pricing.base_price, Decimal('9000.00'))
        self.assertIsNone(pricing.weekend_price)

    def test_invalid_prices_are_rejected(self):
        for bad in ({'base_price': '0'}, {'base_price': '-100'}, {'base_price': 'abc'}, {'base_price': '5000', 'weekend_price': '-1'}):
            r = self.client.post(self.url, bad, format='json')
            self.assertEqual(r.status_code, 400, bad)
        self.assertFalse(Pricing.objects.filter(room_type=self.room).exists())

    def test_platform_fee_and_tax_are_not_owner_controlled(self):
        self.client.post(self.url, {'base_price': '8500.00', 'service_fee_percent': '0', 'tax_percent': '0'}, format='json')
        pricing = Pricing.objects.get(room_type=self.room)
        self.assertEqual(pricing.service_fee_percent, Decimal('5.0'))
        self.assertEqual(pricing.tax_percent, Decimal('10.0'))


class RoomOccupancyDefaultTestCase(APITestCase):
    """The add-room form sends max adults/children but no total_occupancy."""

    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='occ-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.prop = Property.objects.create(
            owner=self.owner, property_type=PropertyType.objects.create(name='Occ Type'), name='Occ Villa',
            description='d', city='Galle', district='Galle', province='Southern', status='draft',
        )
        self.client.force_authenticate(user=self.owner)

    def create_room(self, **fields):
        payload = {'name': 'Room', 'max_adults': 2, 'max_children': 0, 'total_rooms': 1, 'number_of_beds': 1}
        payload.update(fields)
        return self.client.post(f'/api/properties/{self.prop.id}/rooms/', payload, format='json')

    def test_total_occupancy_defaults_to_adults_plus_children(self):
        r = self.create_room(max_adults=4, max_children=2)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(RoomType.objects.get(id=r.data['data']['id']).total_occupancy, 6)

    def test_explicit_total_occupancy_is_kept(self):
        r = self.create_room(max_adults=4, max_children=2, total_occupancy=5)
        self.assertEqual(RoomType.objects.get(id=r.data['data']['id']).total_occupancy, 5)

    def test_invalid_counts_are_rejected(self):
        self.assertEqual(self.create_room(max_adults=0).status_code, 400)
        self.assertEqual(self.create_room(total_rooms=0).status_code, 400)
        self.assertEqual(self.create_room(max_children=-1).status_code, 400)
