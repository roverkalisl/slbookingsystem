"""
Entry Villa (whole-property) workflow.

An Entry Villa's PropertyType has booking_mode='whole_property': the property
itself is the bookable unit. Villa-level capacity/beds/price are stored on one
system-managed "Entire Villa" RoomType (is_property_unit=True, total_rooms=1),
so booking, availability, search, notifications, reviews and payments keep
using the existing room-type architecture. Hotels/resorts/guest houses are
unchanged (booking_mode='room_types').

Run with: python manage.py test apps.properties.tests_entry_villa
"""

import importlib
from datetime import date, timedelta
from decimal import Decimal

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.bookings.models import Availability, Booking
from apps.bookings.service import BookingService
from apps.core.models import Role, UserRole
from .models import Property, PropertyPhoto, PropertyType, Pricing, RoomType, RoomTypePhoto
from .search import PropertySearchService

User = get_user_model()

VILLA_PAYLOAD = {
    'max_adults': 4, 'max_children': 2, 'total_occupancy': 6,
    'number_of_beds': 3, 'bed_configuration': 'king', 'bathroom_type': 'private',
    'base_price': '25000.00', 'weekend_price': '30000.00',
}


def next_monday(min_days_ahead=21):
    start = date.today() + timedelta(days=min_days_ahead)
    return start + timedelta(days=(0 - start.weekday()) % 7)


class EntryVillaTestBase(APITestCase):
    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.owner = User.objects.create_user(email='villa-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.other_owner = User.objects.create_user(email='villa-owner-b@example.com', password='test')
        UserRole.objects.create(user=self.other_owner, role=owner_role)
        self.guest = User.objects.create_user(email='villa-guest@example.com', password='test')
        UserRole.objects.create(user=self.guest, role=guest_role)
        self.guest2 = User.objects.create_user(email='villa-guest2@example.com', password='test')
        UserRole.objects.create(user=self.guest2, role=guest_role)
        self.admin = User.objects.create_user(email='villa-admin@example.com', password='test', is_staff=True)

        self.villa_type = PropertyType.objects.create(name='Entry Villa', booking_mode='whole_property')
        self.hotel_type = PropertyType.objects.create(name='Hotel Test Type')  # default room_types

        self.villa = self.make_property('Tea Garden Villa', self.villa_type)

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return self.client

    def make_property(self, name, property_type, owner=None, status='draft'):
        return Property.objects.create(
            owner=owner or self.owner, property_type=property_type, name=name,
            description='A lovely place', address='1 Estate Road', city='Nuwara Eliya',
            district='Nuwara Eliya', province='Central', status=status,
        )

    def add_property_photos(self, prop, count):
        for i in range(count):
            PropertyPhoto.objects.create(property=prop, cloudinary_url=f'https://res.cloudinary.com/demo/{prop.id}-{i}.jpg',
                                         cloudinary_public_id=f'{prop.id}-{i}', display_order=i)

    def save_villa(self, prop=None, user=None, **overrides):
        return self.as_user(user or self.owner).put(
            f'/api/properties/{(prop or self.villa).id}/villa/', {**VILLA_PAYLOAD, **overrides}, format='json'
        )

    def submit(self, prop=None):
        return self.as_user(self.owner).post(f'/api/properties/{(prop or self.villa).id}/submit-for-approval/')

    def make_ready_villa(self):
        self.add_property_photos(self.villa, 5)
        self.assertEqual(self.save_villa().status_code, 200)

    def approve(self, prop=None):
        prop = prop or self.villa
        self.assertEqual(self.submit(prop).status_code, 200)
        self.assertEqual(self.as_user(self.admin).post(f'/api/properties/{prop.id}/approve/').status_code, 200)


class VillaUnitTestCase(EntryVillaTestBase):

    def test_villa_details_create_one_system_unit(self):
        r = self.save_villa()
        self.assertEqual(r.status_code, 200, r.data)
        units = RoomType.objects.filter(property=self.villa, is_property_unit=True)
        self.assertEqual(units.count(), 1)
        unit = units.get()
        self.assertEqual(unit.name, 'Entire Villa')
        self.assertEqual(unit.total_rooms, 1)
        self.assertTrue(unit.is_active)
        self.assertEqual((unit.max_adults, unit.max_children, unit.total_occupancy), (4, 2, 6))
        self.assertEqual((unit.number_of_beds, unit.bed_configuration, unit.bathroom_type), (3, 'king', 'private'))
        self.assertEqual(unit.pricing.base_price, Decimal('25000.00'))
        self.assertEqual(unit.pricing.weekend_price, Decimal('30000.00'))
        self.assertTrue(r.data['data']['configured'])
        self.assertEqual(self.villa.unit, unit)

    def test_saving_again_updates_the_same_unit(self):
        self.save_villa()
        unit_id = self.villa.unit.id
        r = self.save_villa(max_adults=6, total_occupancy=8, base_price='40000.00', weekend_price=None)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(RoomType.objects.filter(property=self.villa, is_property_unit=True).count(), 1)
        unit = RoomType.objects.get(id=unit_id)
        self.assertEqual(unit.max_adults, 6)
        self.assertEqual(unit.pricing.base_price, Decimal('40000.00'))
        self.assertIsNone(unit.pricing.weekend_price)

    def test_occupancy_defaults_to_adults_plus_children(self):
        payload = {k: v for k, v in VILLA_PAYLOAD.items() if k != 'total_occupancy'}
        r = self.as_user(self.owner).put(f'/api/properties/{self.villa.id}/villa/', payload, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.villa.unit.total_occupancy, 6)

    def test_villa_details_get(self):
        self.assertFalse(self.as_user(self.owner).get(f'/api/properties/{self.villa.id}/villa/').data['data']['configured'])
        self.save_villa()
        data = self.as_user(self.owner).get(f'/api/properties/{self.villa.id}/villa/').data['data']
        self.assertEqual(data['base_price'], '25000.00')
        self.assertEqual(data['max_adults'], 4)

    def test_invalid_villa_details_rejected(self):
        for bad in ({'max_adults': 0}, {'base_price': '0'}, {'bed_configuration': 'hammock'}, {'weekend_price': '-5'}):
            self.assertEqual(self.save_villa(**bad).status_code, 400, bad)
        self.assertIsNone(self.villa.unit)

    def test_villa_details_edit_rules(self):
        self.assertIn(self.save_villa(user=self.other_owner).status_code, (403, 404))
        self.make_ready_villa()
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(self.save_villa(base_price='1.00').status_code, 403)  # pending - not editable
        self.assertEqual(self.villa.unit.pricing.base_price, Decimal('25000.00'))

    def test_villa_endpoint_refused_for_room_based_types(self):
        hotel = self.make_property('City Hotel', self.hotel_type)
        r = self.save_villa(prop=hotel)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(hotel.room_types.exists())

    def test_owner_cannot_create_rooms_for_entry_villa(self):
        r = self.as_user(self.owner).post(f'/api/properties/{self.villa.id}/rooms/', {
            'name': 'Family Room', 'max_adults': 2, 'total_rooms': 1, 'number_of_beds': 1,
        }, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('not applicable for Entry Villa', r.data['error'])
        # The generic room-create route is shadowed by the property detail route
        # (405); the RoomTypeViewSet.perform_create guard is defence in depth.
        r = self.as_user(self.owner).post('/api/properties/rooms/', {
            'property': str(self.villa.id), 'name': 'Upper Room', 'max_adults': 2,
        }, format='json')
        self.assertIn(r.status_code, (400, 405))
        self.assertFalse(self.villa.room_types.exists())

    def test_system_unit_cannot_be_deleted_or_edited_as_a_room(self):
        self.save_villa()
        unit = self.villa.unit
        client = self.as_user(self.owner)
        self.assertEqual(client.delete(f'/api/properties/rooms/{unit.id}/').status_code, 400)
        self.assertEqual(client.patch(f'/api/properties/rooms/{unit.id}/', {'total_rooms': 5}, format='json').status_code, 400)
        unit.refresh_from_db()
        self.assertEqual(unit.total_rooms, 1)

    def test_legacy_rooms_are_deactivated_not_deleted(self):
        """Existing (test) data: owner-created rooms of a villa stop being bookable but are kept."""
        family = RoomType.objects.create(property=self.villa, name='Family Room', max_adults=2, total_occupancy=2, total_rooms=1)
        upper = RoomType.objects.create(property=self.villa, name='Upper Room', max_adults=2, total_occupancy=2, total_rooms=1)
        Pricing.objects.create(room_type=family, base_price=Decimal('9000.00'))
        booking = Booking.objects.create(
            booking_reference='SLB-LEGACY-1', property=self.villa, room_type=family, guest=self.guest,
            check_in_date=next_monday(), check_out_date=next_monday() + timedelta(days=1), number_of_nights=1,
            number_of_adults=1, room_price=Decimal('9000'), subtotal=Decimal('9000'), total_price=Decimal('9000'),
        )
        self.save_villa()
        family.refresh_from_db()
        upper.refresh_from_db()
        self.assertFalse(family.is_active)
        self.assertFalse(upper.is_active)
        self.assertTrue(Booking.objects.filter(id=booking.id).exists())  # never deleted
        self.assertEqual(self.villa.room_types.count(), 3)
        # rooms listing now only exposes the villa unit
        rooms = self.as_user(self.owner).get(f'/api/properties/{self.villa.id}/rooms/').data['data']
        self.assertEqual([r['name'] for r in rooms], ['Entire Villa'])


class VillaSubmissionTestCase(EntryVillaTestBase):

    def test_submits_without_owner_rooms_or_room_photos(self):
        self.make_ready_villa()
        self.assertFalse(RoomTypePhoto.objects.filter(room_type__property=self.villa).exists())
        r = self.submit()
        self.assertEqual(r.status_code, 200, r.data)
        self.villa.refresh_from_db()
        self.assertEqual(self.villa.status, 'pending_approval')

    def test_requires_5_property_photos(self):
        self.add_property_photos(self.villa, 4)
        self.save_villa()
        r = self.submit()
        self.assertEqual(r.status_code, 400)
        self.assertIn('Property must have at least 5 photos (currently 4).', r.data['errors'])

    def test_requires_villa_details(self):
        self.add_property_photos(self.villa, 5)
        r = self.submit()
        self.assertEqual(r.status_code, 400)
        self.assertIn('Villa details have not been set (capacity, beds and nightly price).', r.data['errors'])
        self.assertNotIn('Property must have at least one active room type.', r.data['errors'])

    def test_requires_villa_pricing(self):
        self.make_ready_villa()
        Pricing.objects.filter(room_type=self.villa.unit).delete()
        r = self.submit()
        self.assertIn('Villa pricing has not been configured.', r.data['errors'])

    def test_requires_villa_availability(self):
        self.make_ready_villa()
        RoomType.objects.filter(id=self.villa.unit.id).update(total_rooms=0)
        r = self.submit()
        self.assertIn('Villa availability has not been configured.', r.data['errors'])

    def test_requires_villa_capacity(self):
        self.make_ready_villa()
        RoomType.objects.filter(id=self.villa.unit.id).update(max_adults=0)
        self.assertIn('Villa capacity has not been configured.', self.submit().data['errors'])

    def test_active_owner_rooms_block_submission(self):
        """E.g. a property switched to Entry Villa after rooms were created."""
        self.make_ready_villa()
        RoomType.objects.create(property=self.villa, name='Upper Room', max_adults=2, total_occupancy=2, total_rooms=1)
        r = self.submit()
        self.assertEqual(r.status_code, 400)
        self.assertTrue(any('cannot have separate rooms (Upper Room)' in e for e in r.data['errors']))

    def test_admin_review_shows_villa_and_can_approve(self):
        self.make_ready_villa()
        self.assertEqual(self.submit().status_code, 200)
        detail = self.as_user(self.admin).get(f'/api/properties/{self.villa.id}/').data
        detail = detail.get('data', detail)
        self.assertEqual(detail['booking_mode'], 'whole_property')
        self.assertEqual([r['name'] for r in detail['room_types']], ['Entire Villa'])
        self.assertTrue(detail['room_types'][0]['is_property_unit'])
        self.assertEqual(len(detail['photos']), 5)
        self.assertEqual(self.as_user(self.admin).post(f'/api/properties/{self.villa.id}/approve/').status_code, 200)


class VillaBookingTestCase(EntryVillaTestBase):

    def setUp(self):
        super().setUp()
        self.make_ready_villa()
        self.approve()
        self.villa.refresh_from_db()
        self.unit = RoomType.objects.get(property=self.villa, is_property_unit=True)
        self.check_in = next_monday()
        self.check_out = self.check_in + timedelta(days=2)

    def payload(self, **extra):
        return {'room_type_id': str(self.unit.id), 'check_in_date': str(self.check_in),
                'check_out_date': str(self.check_out), 'number_of_adults': 2, **extra}

    def test_guest_detail_is_the_whole_villa(self):
        self.client.force_authenticate(user=None)
        data = self.client.get(f'/api/properties/{self.villa.id}/').data
        data = data.get('data', data)
        self.assertEqual(data['booking_mode'], 'whole_property')
        self.assertEqual(len(data['room_types']), 1)
        self.assertEqual(data['room_types'][0]['id'], str(self.unit.id))
        self.assertEqual(Decimal(data['min_price']), Decimal('25000.00'))

    def test_guest_books_the_villa_unit(self):
        r = self.as_user(self.guest).post('/api/bookings/', self.payload(), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        booking = Booking.objects.get(id=r.data['data']['id'])
        self.assertEqual(booking.room_type, self.unit)
        self.assertEqual(booking.property, self.villa)
        self.assertEqual(booking.number_of_rooms, 1)
        # 2 weekday nights x 25,000 = 50,000 + 5% fee + 10% tax
        self.assertEqual(booking.subtotal, Decimal('50000.00'))
        self.assertEqual(booking.total_price, Decimal('57750.00'))

    def test_villa_cannot_be_booked_twice_for_same_dates(self):
        self.assertEqual(self.as_user(self.guest).post('/api/bookings/', self.payload(), format='json').status_code, 201)
        r = self.as_user(self.guest2).post('/api/bookings/', self.payload(), format='json')
        self.assertEqual(r.status_code, 409)

    def test_villa_cannot_book_more_than_one_unit(self):
        r = self.as_user(self.guest).post('/api/bookings/', self.payload(number_of_rooms=2), format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('number_of_rooms', r.data)
        q = self.as_user(self.guest).post('/api/bookings/calculate-price/', self.payload(number_of_rooms=2), format='json')
        self.assertEqual(q.status_code, 400)
        with self.assertRaises(ValueError):
            BookingService.create_booking(room_type=self.unit, guest=self.guest, check_in=self.check_in,
                                          check_out=self.check_out, num_adults=2, num_rooms=2)
        self.assertFalse(Booking.objects.filter(property=self.villa).exists())

    def test_villa_capacity_enforced(self):
        r = self.as_user(self.guest).post('/api/bookings/', self.payload(number_of_adults=5), format='json')
        self.assertEqual(r.status_code, 400)

    def test_quote_matches_booking(self):
        quote = self.as_user(self.guest).post('/api/bookings/calculate-price/', self.payload(), format='json')
        self.assertEqual(quote.status_code, 200, quote.data)
        created = self.as_user(self.guest).post('/api/bookings/', self.payload(), format='json')
        self.assertEqual(Decimal(str(quote.data['data']['total'])), Decimal(str(created.data['data']['total_price'])))

    def test_owner_blocked_dates_make_villa_unavailable(self):
        Availability.objects.create(room_type=self.unit, date=self.check_in, status='blocked', available_count=0)
        r = self.as_user(self.guest).post('/api/bookings/', self.payload(), format='json')
        self.assertEqual(r.status_code, 409)

    def test_booking_lifecycle_compatible(self):
        """Owner confirm, review, cancellation and offline payment all work for villa bookings."""
        booking_id = self.as_user(self.guest).post('/api/bookings/', self.payload(), format='json').data['data']['id']
        self.assertEqual(self.as_user(self.owner).post(f'/api/bookings/{booking_id}/confirm/').status_code, 200)
        review = self.as_user(self.guest).post('/api/reviews/', {
            'booking_id': booking_id, 'rating': 5, 'title': 'Lovely villa', 'comment': 'Great stay.',
        }, format='json')
        self.assertEqual(review.status_code, 201, review.content)
        pay = self.as_user(self.guest).post('/api/payments/initiate/', {
            'booking_id': booking_id, 'payment_method': 'pay_at_property',
        }, format='json')
        self.assertEqual(pay.status_code, 200, pay.data)
        self.assertEqual(Decimal(str(pay.data['data']['amount'])), Decimal('57750.00'))
        cancel = self.as_user(self.guest).post(f'/api/bookings/{booking_id}/cancel/', {}, format='json')
        self.assertEqual(cancel.status_code, 200)
        # released - the villa can be booked again for those dates
        self.assertEqual(self.as_user(self.guest2).post('/api/bookings/', self.payload(), format='json').status_code, 201)


class VillaSearchTestCase(EntryVillaTestBase):

    def setUp(self):
        super().setUp()
        # Legacy (inactive) owner room with very different price/capacity must never drive search
        legacy = RoomType.objects.create(property=self.villa, name='Old Room', max_adults=10, total_occupancy=10,
                                         total_rooms=3)
        Pricing.objects.create(room_type=legacy, base_price=Decimal('1000.00'))
        self.make_ready_villa()  # deactivates the legacy room, creates the unit (25,000, 4 adults)
        self.approve()

        self.hotel = self.make_property('Lake Hotel', self.hotel_type, status='approved')
        for name, price, adults, units in (('Standard', '8000.00', 2, 3), ('Suite', '20000.00', 4, 1)):
            room = RoomType.objects.create(property=self.hotel, name=name, max_adults=adults,
                                           total_occupancy=adults, total_rooms=units)
            Pricing.objects.create(room_type=room, base_price=Decimal(price))
        self.check_in = next_monday()
        self.check_out = self.check_in + timedelta(days=2)

    def names(self, service):
        return set(service.queryset.values_list('name', flat=True))

    def test_price_filter_uses_villa_price(self):
        self.assertNotIn('Tea Garden Villa', self.names(PropertySearchService().filter_by_price_range(Decimal('500'), Decimal('2000'))))
        self.assertIn('Tea Garden Villa', self.names(PropertySearchService().filter_by_price_range(Decimal('20000'), Decimal('30000'))))

    def test_capacity_filter_uses_villa_capacity(self):
        self.assertIn('Tea Garden Villa', self.names(PropertySearchService().filter_by_occupancy(num_adults=4)))
        self.assertNotIn('Tea Garden Villa', self.names(PropertySearchService().filter_by_occupancy(num_adults=8)))

    def test_availability_uses_single_villa_unit(self):
        self.assertIn('Tea Garden Villa', self.names(PropertySearchService().filter_by_availability(self.check_in, self.check_out)))
        unit = RoomType.objects.get(property=self.villa, is_property_unit=True)  # fresh (approved) property
        BookingService.create_booking(room_type=unit, guest=self.guest,
                                      check_in=self.check_in, check_out=self.check_out, num_adults=2)
        self.assertNotIn('Tea Garden Villa', self.names(PropertySearchService().filter_by_availability(self.check_in, self.check_out)))

    def test_room_based_search_unchanged(self):
        self.assertIn('Lake Hotel', self.names(PropertySearchService().filter_by_price_range(Decimal('7000'), Decimal('9000'))))
        self.assertIn('Lake Hotel', self.names(PropertySearchService().filter_by_occupancy(num_adults=4)))
        hotel_std = self.hotel.room_types.get(name='Standard')
        BookingService.create_booking(room_type=hotel_std, guest=self.guest,
                                      check_in=self.check_in, check_out=self.check_out, num_adults=1, num_rooms=3)
        # Suite still free -> hotel still available
        self.assertIn('Lake Hotel', self.names(PropertySearchService().filter_by_availability(self.check_in, self.check_out)))

    def test_search_cards_show_villa_price(self):
        self.client.force_authenticate(user=None)
        r = self.client.get('/api/properties/search/advanced/?city=Nuwara Eliya')
        results = r.data.get('results') or r.data.get('data') or []
        villa = next(p for p in results if p['name'] == 'Tea Garden Villa')
        self.assertEqual(Decimal(villa['min_price']), Decimal('25000.00'))
        self.assertEqual(villa['room_count'], 1)

    def test_property_without_type_still_searchable(self):
        untyped = Property.objects.create(owner=self.owner, property_type=None, name='No Type Lodge',
                                          description='d', city='Ella', district='Badulla', province='Uva', status='approved')
        room = RoomType.objects.create(property=untyped, name='Room', max_adults=2, total_occupancy=2, total_rooms=1)
        Pricing.objects.create(room_type=room, base_price=Decimal('5000.00'))
        self.assertIn('No Type Lodge', self.names(PropertySearchService().filter_by_price_range(Decimal('4000'), Decimal('6000'))))


class RoomBasedWorkflowUnchangedTestCase(EntryVillaTestBase):

    def test_hotel_rooms_and_submission_unchanged(self):
        hotel = self.make_property('Harbour Hotel', self.hotel_type)
        client = self.as_user(self.owner)
        r = client.post(f'/api/properties/{hotel.id}/rooms/', {
            'name': 'Deluxe', 'max_adults': 2, 'total_rooms': 4, 'number_of_beds': 1,
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertFalse(RoomType.objects.get(id=r.data['data']['id']).is_property_unit)
        self.add_property_photos(hotel, 5)
        errors = self.submit(hotel).data['errors']
        self.assertIn("Room 'Deluxe' must have at least 1 photo.", errors)
        self.assertIn("Room 'Deluxe' does not have pricing configured.", errors)
        detail = client.get(f'/api/properties/{hotel.id}/').data
        detail = detail.get('data', detail)
        self.assertEqual(detail['booking_mode'], 'room_types')

    def test_hotel_multi_room_booking_unchanged(self):
        hotel = self.make_property('Bay Hotel', self.hotel_type, status='approved')
        room = RoomType.objects.create(property=hotel, name='Twin', max_adults=2, total_occupancy=2, total_rooms=3)
        Pricing.objects.create(room_type=room, base_price=Decimal('10000.00'))
        booking = BookingService.create_booking(room_type=room, guest=self.guest, check_in=next_monday(),
                                                check_out=next_monday() + timedelta(days=1), num_adults=4, num_rooms=2)
        self.assertEqual(booking.number_of_rooms, 2)


class EntryVillaDataMigrationTestCase(APITestCase):

    def test_migration_sets_entry_villa_by_name_only(self):
        migration = importlib.import_module('apps.properties.migrations.0006_entry_villa_whole_property')
        villa = PropertyType.objects.create(name='entry villa')  # case-insensitive match
        hotel = PropertyType.objects.create(name='Hotel For Migration')
        plain_villa = PropertyType.objects.create(name='Villa For Migration')
        migration.set_entry_villa_whole_property(django_apps, None)
        villa.refresh_from_db(); hotel.refresh_from_db(); plain_villa.refresh_from_db()
        self.assertEqual(villa.booking_mode, 'whole_property')
        self.assertEqual(villa.name, 'entry villa')  # name and id untouched
        self.assertEqual(hotel.booking_mode, 'room_types')
        self.assertEqual(plain_villa.booking_mode, 'room_types')
