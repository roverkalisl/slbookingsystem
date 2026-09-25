"""
Owner property isolation (IDOR) audit.

Owner A and Owner B each have an APPROVED property (visible to everyone, the
worst case for IDOR - it is in every owner's read queryset) and a DRAFT
property, each with a room, pricing, property/room photos, a booking and a
review. Every owner-facing endpoint is attacked with the other owner's ids
(property, room, photo, booking, review - in the URL and in the payload) and
must answer 403/404 without changing anything. Both directions are tested,
the rightful owner keeps working, and an admin can still manage both.

Run with: python manage.py test apps.properties.tests_owner_isolation
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.bookings.models import Availability, Booking
from apps.core.models import Role, UserRole
from apps.reviews.models import Review, ReviewResponse
from .models import Pricing, Property, PropertyPhoto, PropertyType, RoomType, RoomTypePhoto

User = get_user_model()
DENIED = (403, 404)


class OwnerIsolationTestCase(APITestCase):
    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.hotel = PropertyType.objects.create(name='Isolation Hotel')
        self.guest = User.objects.create_user(email='iso-guest@example.com', password='x', phone='0770000000')
        UserRole.objects.create(user=self.guest, role=guest_role)
        self.admin = User.objects.create_user(email='iso-admin@example.com', password='x',
                                              is_staff=True, is_superuser=True)
        self.a = self.make_world('a', owner_role)
        self.b = self.make_world('b', owner_role)

    # ------------------------------------------------------------ fixtures

    def make_world(self, tag, owner_role):
        owner = User.objects.create_user(email=f'iso-owner-{tag}@example.com', password='x')
        UserRole.objects.create(user=owner, role=owner_role)
        world = {'owner': owner}
        for kind, status in (('approved', 'approved'), ('draft', 'draft')):
            prop = Property.objects.create(owner=owner, property_type=self.hotel, name=f'{tag}-{kind}',
                                           description='d', city='Galle', district='Galle',
                                           province='Southern', status=status)
            room = RoomType.objects.create(property=prop, name=f'{tag}-{kind}-room', max_adults=2,
                                           total_occupancy=2, total_rooms=2)
            Pricing.objects.create(room_type=room, base_price=Decimal('10000.00'))
            for i in range(2):
                PropertyPhoto.objects.create(property=prop, cloudinary_url=f'https://res.cloudinary.com/demo/{tag}{kind}{i}.jpg',
                                             cloudinary_public_id=f'{tag}{kind}{i}', display_order=i, is_cover=(i == 0))
            room_photo = RoomTypePhoto.objects.create(room_type=room, cloudinary_url=f'https://res.cloudinary.com/demo/r{tag}{kind}.jpg',
                                                      cloudinary_public_id=f'r{tag}{kind}')
            world[kind] = {'property': prop, 'room': room, 'room_photo': room_photo,
                           'photos': list(prop.photos.order_by('display_order'))}
        check_in = date.today() + timedelta(days=20)
        booking = Booking.objects.create(
            booking_reference=f'ISO-{tag.upper()}', property=world['approved']['property'],
            room_type=world['approved']['room'], guest=self.guest, check_in_date=check_in,
            check_out_date=check_in + timedelta(days=2), number_of_nights=2, number_of_adults=2,
            room_price=Decimal('10000'), subtotal=Decimal('20000'), total_price=Decimal('20000'), status='pending',
        )
        world['booking'] = booking
        world['review'] = Review.objects.create(booking=booking, property=booking.property, guest=self.guest,
                                                overall_rating=5, comment='nice')
        return world

    def as_user(self, user):
        self.client.force_authenticate(user)

    def assertDenied(self, response, msg=''):
        self.assertIn(response.status_code, DENIED, f'{msg}: expected 403/404, got {response.status_code}')

    @staticmethod
    def results(response):
        data = response.data
        if isinstance(data, dict):
            data = data.get('results', data.get('data', data))
        return data

    # ------------------------------------------------------------ attacks

    def attack(self, attacker, victim, mine):
        """`attacker` (owner of world `mine`) tries every owner action on world `victim`."""
        self.as_user(attacker)
        v_app, v_draft = victim['approved'], victim['draft']
        v_prop, v_room = v_app['property'], v_app['room']

        # --- property ---
        ids = {row['id'] for row in self.results(self.client.get('/api/properties/'))}
        self.assertNotIn(str(v_prop.id), ids, 'other owner property in My Properties list')
        self.assertNotIn(str(v_draft['property'].id), ids)
        self.assertEqual(self.client.get(f"/api/properties/{v_draft['property'].id}/").status_code, 404)
        detail = self.client.get(f'/api/properties/{v_prop.id}/')  # public listing page - allowed
        self.assertEqual(detail.status_code, 200)
        self.assertIsNone(detail.data['owner_email'], 'owner email leaked')
        self.assertIsNone(detail.data['owner_name'], 'owner name leaked')
        for target in (v_prop, v_draft['property']):
            self.assertDenied(self.client.patch(f'/api/properties/{target.id}/', {'name': 'hacked'}, format='json'), 'update')
            # Not an Entry Villa -> 400 "not a villa" before any write; never 2xx
            self.assertIn(self.client.put(f'/api/properties/{target.id}/villa/', {}, format='json').status_code,
                          (400, 403, 404), 'villa')
            self.assertDenied(self.client.post(f'/api/properties/{target.id}/submit-for-approval/'), 'submit')
            self.assertDenied(self.client.delete(f'/api/properties/{target.id}/'), 'delete')
        self.assertDenied(self.client.get(f"/api/properties/{v_draft['property'].id}/photos/"), 'draft photos')

        # --- property photos ---
        photo = {'cloudinary_url': 'https://res.cloudinary.com/demo/x.jpg', 'cloudinary_public_id': 'x'}
        for target in (v_prop, v_draft['property']):
            self.assertDenied(self.client.get(f'/api/properties/{target.id}/upload-signature/'), 'signature')
            self.assertDenied(self.client.post(f'/api/properties/{target.id}/photos/', photo, format='json'), 'upload')
        victim_photo = v_app['photos'][1]
        self.assertDenied(self.client.delete(f'/api/properties/{v_prop.id}/delete-photo/?photo_id={victim_photo.id}'), 'photo delete')
        self.assertDenied(self.client.post(f'/api/properties/{v_prop.id}/set-cover/', {'photo_id': str(victim_photo.id)}, format='json'), 'set cover')
        # IDOR through my own property's URL with the victim's photo id
        my_prop = mine['draft']['property']
        self.assertEqual(self.client.delete(f'/api/properties/{my_prop.id}/delete-photo/?photo_id={victim_photo.id}').status_code, 404)
        self.assertEqual(self.client.post(f'/api/properties/{my_prop.id}/set-cover/', {'photo_id': str(victim_photo.id)}, format='json').status_code, 404)

        # --- rooms ---
        room_payload = {'name': 'Injected', 'room_type': 'double', 'max_adults': 2, 'max_children': 0,
                        'bed_configuration': 'double', 'bathroom_type': 'private', 'number_of_beds': 1, 'total_rooms': 1}
        self.assertDenied(self.client.post(f'/api/properties/{v_prop.id}/rooms/', room_payload, format='json'), 'room create')
        self.assertIn(self.client.post('/api/properties/rooms/', {**room_payload, 'property': str(v_prop.id)}, format='json').status_code,
                      (403, 404, 405), 'room create via payload')
        self.assertDenied(self.client.patch(f'/api/properties/rooms/{v_room.id}/', {'name': 'hacked'}, format='json'), 'room update')
        self.assertDenied(self.client.delete(f'/api/properties/rooms/{v_room.id}/'), 'room delete')
        self.assertEqual(self.client.get(f"/api/properties/rooms/{v_draft['room'].id}/").status_code, 404)
        # IDOR through the payload: move MY room into the victim's property
        my_room = mine['draft']['room']
        self.assertDenied(self.client.patch(f'/api/properties/rooms/{my_room.id}/', {'property': str(v_prop.id)}, format='json'),
                          'room reassigned to victim property')
        my_room.refresh_from_db()
        self.assertEqual(my_room.property_id, mine['draft']['property'].id)

        # --- room photos ---
        self.assertDenied(self.client.get(f'/api/properties/rooms/{v_room.id}/upload-signature/'), 'room signature')
        self.assertDenied(self.client.post(f'/api/properties/rooms/{v_room.id}/add-photo/', photo, format='json'), 'room photo upload')
        self.assertDenied(self.client.delete(f"/api/properties/rooms/{v_room.id}/delete-photo/?photo_id={v_app['room_photo'].id}"), 'room photo delete')
        self.assertEqual(self.client.delete(
            f"/api/properties/rooms/{my_room.id}/delete-photo/?photo_id={v_app['room_photo'].id}").status_code, 404)
        self.assertEqual(self.client.delete(
            f'/api/properties/rooms/{my_room.id}/delete-photo/?photo_id=not-a-uuid').status_code, 404)

        # --- pricing ---
        self.assertDenied(self.client.post(f'/api/properties/rooms/{v_room.id}/pricing/', {'base_price': '1.00'}, format='json'), 'pricing')
        self.assertDenied(self.client.get(f"/api/properties/rooms/{v_draft['room'].id}/pricing/"), 'draft pricing view')

        # --- availability ---
        dates = {'start_date': (date.today() + timedelta(days=30)).isoformat(),
                 'end_date': (date.today() + timedelta(days=31)).isoformat()}
        self.assertDenied(self.client.get(f'/api/properties/rooms/{v_room.id}/calendar/'), 'calendar')
        self.assertDenied(self.client.post(f'/api/properties/rooms/{v_room.id}/block-dates/', dates, format='json'), 'block')
        self.assertDenied(self.client.post(f'/api/properties/rooms/{v_room.id}/unblock-dates/', dates, format='json'), 'unblock')

        # --- bookings ---
        booking = victim['booking']
        refs = {row['booking_reference'] for row in self.results(self.client.get('/api/bookings/'))}
        self.assertNotIn(booking.booking_reference, refs, 'other owner booking listed')
        self.assertDenied(self.client.get(f'/api/bookings/{booking.id}/'), 'booking detail')
        for action in ('confirm', 'reject', 'confirm_payment', 'cancel'):
            self.assertDenied(self.client.post(f'/api/bookings/{booking.id}/{action}/', {}, format='json'), f'booking {action}')

        # --- reviews ---
        self.assertDenied(self.client.post(f"/api/reviews/{victim['review'].id}/response/",
                                           {'response_text': 'hijack'}, format='json'), 'review response')

    def assert_victim_untouched(self, victim):
        for kind in ('approved', 'draft'):
            world = victim[kind]
            prop = Property.objects.get(pk=world['property'].pk)
            self.assertEqual(prop.name, world['property'].name)
            self.assertEqual(prop.status, world['property'].status)
            self.assertEqual(PropertyPhoto.objects.filter(property=prop).count(), 2)
            self.assertEqual(PropertyPhoto.objects.get(property=prop, is_cover=True).pk, world['photos'][0].pk)
            self.assertEqual(list(RoomType.objects.filter(property=prop).values_list('pk', flat=True)), [world['room'].pk])
            self.assertEqual(RoomType.objects.get(pk=world['room'].pk).name, world['room'].name)
            self.assertTrue(RoomTypePhoto.objects.filter(pk=world['room_photo'].pk).exists())
            self.assertEqual(RoomTypePhoto.objects.filter(room_type=world['room']).count(), 1)
            self.assertEqual(Pricing.objects.get(room_type=world['room']).base_price, Decimal('10000.00'))
            self.assertFalse(Availability.objects.filter(room_type=world['room']).exists())
        booking = Booking.objects.get(pk=victim['booking'].pk)
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.payment_status, 'pending')
        self.assertFalse(ReviewResponse.objects.filter(review=victim['review']).exists())

    def test_owner_a_cannot_touch_owner_b(self):
        self.attack(self.a['owner'], victim=self.b, mine=self.a)
        self.assert_victim_untouched(self.b)

    def test_owner_b_cannot_touch_owner_a(self):
        self.attack(self.b['owner'], victim=self.a, mine=self.b)
        self.assert_victim_untouched(self.a)

    # ------------------------------------------------------------ rightful owner

    def manage_own(self, world):
        self.as_user(world['owner'])
        prop, room = world['draft']['property'], world['draft']['room']
        ids = {row['id'] for row in self.results(self.client.get('/api/properties/'))}
        self.assertEqual(ids, {str(world['approved']['property'].id), str(prop.id)})
        detail = self.client.get(f'/api/properties/{prop.id}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['owner_email'], world['owner'].email)
        self.assertEqual(self.client.patch(f'/api/properties/{prop.id}/', {'name': 'renamed'}, format='json').status_code, 200)
        photo = self.client.post(f'/api/properties/{prop.id}/photos/',
                                 {'cloudinary_url': 'https://res.cloudinary.com/demo/new.jpg', 'cloudinary_public_id': 'new'},
                                 format='json')
        self.assertEqual(photo.status_code, 201)
        self.assertEqual(self.client.post(f'/api/properties/{prop.id}/set-cover/', {'photo_id': photo.data['data']['id']},
                                          format='json').status_code, 200)
        self.assertEqual(self.client.delete(f"/api/properties/{prop.id}/delete-photo/?photo_id={world['draft']['photos'][1].id}").status_code, 200)
        self.assertEqual(self.client.patch(f'/api/properties/rooms/{room.id}/', {'name': 'Suite'}, format='json').status_code, 200)
        self.assertEqual(self.client.post(f'/api/properties/rooms/{room.id}/add-photo/',
                                          {'cloudinary_url': 'https://res.cloudinary.com/demo/rn.jpg', 'cloudinary_public_id': 'rn'},
                                          format='json').status_code, 201)
        self.assertEqual(self.client.delete(
            f"/api/properties/rooms/{room.id}/delete-photo/?photo_id={world['draft']['room_photo'].id}").status_code, 200)
        self.assertEqual(self.client.post(f'/api/properties/rooms/{room.id}/pricing/', {'base_price': '12000.00'},
                                          format='json').status_code, 200)
        dates = {'start_date': (date.today() + timedelta(days=40)).isoformat(),
                 'end_date': (date.today() + timedelta(days=41)).isoformat()}
        self.assertEqual(self.client.post(f'/api/properties/rooms/{room.id}/block-dates/', dates, format='json').status_code, 200)
        self.assertEqual(self.client.get(f'/api/properties/rooms/{room.id}/calendar/').status_code, 200)
        refs = {row['booking_reference'] for row in self.results(self.client.get('/api/bookings/'))}
        self.assertEqual(refs, {world['booking'].booking_reference})
        self.assertEqual(self.client.get(f"/api/bookings/{world['booking'].id}/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/bookings/{world['booking'].id}/confirm/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/reviews/{world['review'].id}/response/",
                                          {'response_text': 'Thank you!'}, format='json').status_code, 201)

    def test_owner_a_manages_own_properties(self):
        self.manage_own(self.a)

    def test_owner_b_manages_own_properties(self):
        self.manage_own(self.b)

    # ------------------------------------------------------------ admin

    def test_admin_can_manage_both_owners(self):
        self.as_user(self.admin)
        ids = {row['id'] for row in self.results(self.client.get('/api/properties/'))}
        for world in (self.a, self.b):
            prop, room = world['approved']['property'], world['approved']['room']
            self.assertIn(str(prop.id), ids)
            self.assertIn(str(world['draft']['property'].id), ids)
            detail = self.client.get(f'/api/properties/{prop.id}/')
            self.assertEqual(detail.data['owner_email'], world['owner'].email)
            self.assertEqual(self.client.patch(f'/api/properties/{prop.id}/', {'name': 'admin-edit'}, format='json').status_code, 200)
            self.assertEqual(self.client.post(f'/api/properties/{prop.id}/set-cover/',
                                              {'photo_id': str(world['approved']['photos'][1].id)}, format='json').status_code, 200)
            self.assertEqual(self.client.patch(f'/api/properties/rooms/{room.id}/', {'name': 'admin-room'}, format='json').status_code, 200)
            self.assertEqual(self.client.post(f'/api/properties/rooms/{room.id}/pricing/', {'base_price': '9000.00'},
                                              format='json').status_code, 200)
            self.assertEqual(self.client.get(f'/api/properties/rooms/{room.id}/calendar/').status_code, 200)
            self.assertEqual(self.client.get(f"/api/bookings/{world['booking'].id}/").status_code, 200)
            self.assertEqual(self.client.post(f"/api/bookings/{world['booking'].id}/confirm/").status_code, 200)
            self.assertEqual(self.client.delete(f"/api/properties/{world['draft']['property'].id}/").status_code, 204)

    def test_guest_and_anonymous_see_only_public_data(self):
        self.as_user(self.guest)
        ids = {row['id'] for row in self.results(self.client.get('/api/properties/'))}
        self.assertEqual(ids, {str(self.a['approved']['property'].id), str(self.b['approved']['property'].id)})
        self.assertDenied(self.client.patch(f"/api/properties/{self.a['approved']['property'].id}/", {'name': 'x'}, format='json'))
        self.client.force_authenticate(None)
        detail = self.client.get(f"/api/properties/{self.a['approved']['property'].id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertIsNone(detail.data['owner_email'])
        self.assertEqual(self.client.get(f"/api/properties/{self.a['draft']['property'].id}/").status_code, 404)
