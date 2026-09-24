"""
Tests for submit-for-approval requirements and photo rules.

A property may be saved as an incomplete draft, but can only be submitted for
admin approval once it has complete details, at least 5 property photos (no
maximum of 5), at least one active room, and every active room has 1-5 photos
(minimum 1 at submission, maximum 5 enforced on upload), pricing and bookable
inventory.

Run with: python manage.py test apps.properties.tests_submission
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.models import Role, UserRole
from .models import Property, PropertyType, PropertyPhoto, RoomType, RoomTypePhoto, Pricing

User = get_user_model()


class SubmitForApprovalTestCase(APITestCase):
    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='submit-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.admin = User.objects.create_user(email='submit-admin@example.com', password='test', is_staff=True)

        self.property_type = PropertyType.objects.create(name='Submission Villa Type')
        self.property = Property.objects.create(
            owner=self.owner, property_type=self.property_type, name='Submission Villa',
            description='A lovely villa', address='1 Beach Road', city='Galle',
            district='Galle', province='Southern', status='draft',
        )
        self.room = RoomType.objects.create(
            property=self.property, name='Deluxe Room', max_adults=2, total_occupancy=2, total_rooms=2
        )
        Pricing.objects.create(room_type=self.room, base_price=Decimal('12000.00'))

        self.add_property_photos(5)
        self.add_room_photos(self.room, 1)  # the minimum - so a complete property uses just 1 room photo

    def add_property_photos(self, count):
        start = self.property.photos.count()
        for index in range(start, start + count):
            PropertyPhoto.objects.create(
                property=self.property,
                cloudinary_url=f'https://res.cloudinary.com/demo/property-{index}.jpg',
                cloudinary_public_id=f'property-{index}',
                display_order=index,
            )

    def add_room_photos(self, room, count):
        start = room.photos.count()
        for index in range(start, start + count):
            RoomTypePhoto.objects.create(
                room_type=room,
                cloudinary_url=f'https://res.cloudinary.com/demo/{room.id}-{index}.jpg',
                cloudinary_public_id=f'{room.id}-{index}',
                display_order=index,
            )

    def submit(self):
        self.client.force_authenticate(self.owner)
        return self.client.post(f'/api/properties/{self.property.id}/submit-for-approval/')

    def assert_rejected_with(self, response, message):
        self.assertEqual(response.status_code, 400)
        self.assertIn(message, ' '.join(response.data['errors']))
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, 'draft')

    def assert_submitted(self, response):
        self.assertEqual(response.status_code, 200, response.data)
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, 'pending_approval')
        self.assertIsNotNone(self.property.submitted_at)

    # --- Property photos -------------------------------------------------

    def test_fewer_than_5_property_photos_is_rejected(self):
        self.property.photos.first().delete()
        self.assert_rejected_with(self.submit(), 'Property must have at least 5 photos')

    def test_exactly_5_property_photos_is_accepted(self):
        self.assertEqual(self.property.photos.count(), 5)
        self.assert_submitted(self.submit())

    def test_more_than_5_property_photos_is_accepted(self):
        self.add_property_photos(7)
        self.assert_submitted(self.submit())

    # --- Room photos -----------------------------------------------------

    def test_room_with_0_photos_is_rejected(self):
        self.room.photos.all().delete()
        response = self.submit()
        self.assert_rejected_with(response, "Room 'Deluxe Room' must have at least 1 photo.")

    def test_room_with_1_to_5_photos_is_accepted(self):
        for count in range(1, 6):
            with self.subTest(room_photos=count):
                self.add_room_photos(self.room, count - self.room.photos.count())
                self.assertEqual(self.room.photos.count(), count)
                Property.objects.filter(id=self.property.id).update(status='draft', submitted_at=None)
                self.assert_submitted(self.submit())

    def test_room_with_existing_photos_above_5_is_still_valid_and_untouched(self):
        """Rooms that got more than 5 photos before the cap existed are not
        rejected, and their photos are never deleted automatically."""
        self.add_room_photos(self.room, 6)  # 7 total, created directly (pre-cap data)
        ids_before = set(self.room.photos.values_list('id', flat=True))
        self.assert_submitted(self.submit())
        self.assertEqual(set(self.room.photos.values_list('id', flat=True)), ids_before)

    def test_every_active_room_needs_at_least_1_photo(self):
        second_room = RoomType.objects.create(
            property=self.property, name='Garden Suite', max_adults=2, total_occupancy=2, total_rooms=1
        )
        Pricing.objects.create(room_type=second_room, base_price=Decimal('15000.00'))
        self.assert_rejected_with(self.submit(), "Room 'Garden Suite' must have at least 1 photo.")

        self.add_room_photos(second_room, 1)
        self.assert_submitted(self.submit())

    def test_property_photo_minimum_is_unchanged(self):
        """This change is room-only: properties still need at least 5 photos."""
        self.property.photos.first().delete()
        self.assert_rejected_with(self.submit(), 'Property must have at least 5 photos')

    def test_inactive_room_is_not_required_to_be_complete(self):
        RoomType.objects.create(
            property=self.property, name='Closed Wing', max_adults=2, total_occupancy=2,
            total_rooms=1, is_active=False
        )
        self.assert_submitted(self.submit())

    # --- Pricing / availability / rooms ----------------------------------

    def test_missing_pricing_is_rejected(self):
        Pricing.objects.filter(room_type=self.room).delete()
        self.assert_rejected_with(self.submit(), "Room 'Deluxe Room' does not have pricing configured.")

    def test_missing_availability_is_rejected(self):
        self.room.total_rooms = 0
        self.room.save()
        self.assert_rejected_with(self.submit(), "Availability has not been configured for room 'Deluxe Room'")

    def test_no_room_types_is_rejected(self):
        self.room.delete()
        self.assert_rejected_with(self.submit(), 'Property must have at least one active room type.')

    def test_missing_required_fields_is_rejected(self):
        self.property.address = ''
        self.property.save()
        self.assert_rejected_with(self.submit(), 'Missing required fields: address.')

    def test_all_problems_are_reported_together(self):
        self.property.photos.first().delete()
        Pricing.objects.filter(room_type=self.room).delete()
        response = self.submit()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(response.data['errors']), 2)
        self.assertIn('detail', response.data)

    # --- Full workflow ---------------------------------------------------

    def test_fully_complete_property_submits_successfully(self):
        self.assert_submitted(self.submit())

    def test_admin_can_approve_submitted_property(self):
        self.assert_submitted(self.submit())

        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/api/properties/{self.property.id}/approve/')

        self.assertEqual(response.status_code, 200)
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, 'approved')

    def test_admin_can_reject_and_owner_can_resubmit(self):
        self.assert_submitted(self.submit())

        self.client.force_authenticate(self.admin)
        response = self.client.post(
            f'/api/properties/{self.property.id}/reject/', {'rejection_reason': 'Blurry photos'}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, 'rejected')

        self.assert_submitted(self.submit())

    def test_other_owner_cannot_submit(self):
        owner_role = Role.objects.get(name='property_owner')
        other = User.objects.create_user(email='submit-other@example.com', password='test')
        UserRole.objects.create(user=other, role=owner_role)

        self.client.force_authenticate(other)
        response = self.client.post(f'/api/properties/{self.property.id}/submit-for-approval/')

        self.assertIn(response.status_code, [403, 404])
        self.property.refresh_from_db()
        self.assertEqual(self.property.status, 'draft')


class DraftAndPhotoLimitTestCase(APITestCase):
    """Drafts stay saveable while incomplete; rooms accept at most 5 photos (server-side)."""

    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='draft-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.property_type = PropertyType.objects.create(name='Draft Apartment Type')
        self.client.force_authenticate(self.owner)

    def test_incomplete_draft_can_still_be_saved(self):
        response = self.client.post('/api/properties/', {
            'property_type': self.property_type.id,
            'name': 'Unfinished Apartment',
            'description': 'No photos or rooms yet',
            'city': 'Colombo',
            'district': 'Colombo',
            'province': 'Western',
            'status': 'draft',
        }, format='json')

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Property.objects.get(name='Unfinished Apartment').status, 'draft')

    def make_room(self, name='Studio'):
        property_obj = Property.objects.create(
            owner=self.owner, property_type=self.property_type, name=f'{name} Apartment',
            description='desc', city='Colombo', district='Colombo', province='Western', status='draft',
        )
        return RoomType.objects.create(
            property=property_obj, name=name, max_adults=2, total_occupancy=2, total_rooms=1
        )

    def upload(self, room, label):
        return self.client.post(f'/api/properties/rooms/{room.id}/add-photo/', {
            'cloudinary_url': f'https://res.cloudinary.com/demo/{label}.jpg',
            'cloudinary_public_id': label,
        }, format='json')

    def test_room_accepts_1_to_5_photos_via_api(self):
        room = self.make_room()
        for index in range(5):
            response = self.upload(room, f'studio-{index}')
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(room.photos.count(), index + 1)

    def test_sixth_room_photo_is_rejected_and_existing_photos_kept(self):
        room = self.make_room()
        for index in range(5):
            self.upload(room, f'studio-{index}')
        ids_before = set(room.photos.values_list('id', flat=True))

        response = self.upload(room, 'studio-6th')
        self.assertEqual(response.status_code, 400)
        self.assertIn('at most 5 photos', response.data['error'])
        self.assertEqual(room.photos.count(), 5)
        self.assertEqual(set(room.photos.values_list('id', flat=True)), ids_before)  # nothing deleted
        self.assertFalse(RoomTypePhoto.objects.filter(cloudinary_public_id='studio-6th').exists())

    def test_upload_allowed_again_after_deleting_a_photo(self):
        room = self.make_room()
        for index in range(5):
            self.upload(room, f'studio-{index}')
        photo = room.photos.first()
        self.assertEqual(self.client.delete(f'/api/properties/rooms/{room.id}/delete-photo/?photo_id={photo.id}').status_code, 200)
        self.assertEqual(self.upload(room, 'studio-replacement').status_code, 201)
        self.assertEqual(room.photos.count(), 5)

    def test_room_with_legacy_photos_above_5_rejects_uploads_but_keeps_photos(self):
        room = self.make_room()
        for index in range(7):  # created before the cap existed
            RoomTypePhoto.objects.create(room_type=room, cloudinary_url=f'https://res.cloudinary.com/demo/l{index}.jpg',
                                         cloudinary_public_id=f'legacy-{index}')
        self.assertEqual(self.upload(room, 'legacy-new').status_code, 400)
        self.assertEqual(room.photos.count(), 7)

    def test_limit_is_per_room(self):
        full_room = self.make_room('Full')
        for index in range(5):
            self.upload(full_room, f'full-{index}')
        other_room = self.make_room('Empty')
        self.assertEqual(self.upload(other_room, 'other-0').status_code, 201)

    def test_property_photos_still_have_no_maximum_of_5(self):
        """Room-only change: the 6th+ PROPERTY photo is still accepted."""
        property_obj = self.make_room('PropPhotos').property
        for index in range(7):
            response = self.client.post(f'/api/properties/{property_obj.id}/photos/', {
                'cloudinary_url': f'https://res.cloudinary.com/demo/prop-{index}.jpg',
                'cloudinary_public_id': f'prop-{index}',
            }, format='json')
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(property_obj.photos.count(), 7)

    def test_photo_delete_urls_used_by_frontend_are_routed(self):
        """lib/api.ts calls the hyphenated delete-photo URLs for properties and rooms."""
        property_obj = Property.objects.create(
            owner=self.owner, property_type=self.property_type, name='Delete Apartment',
            description='desc', city='Colombo', district='Colombo', province='Western', status='draft',
        )
        room = RoomType.objects.create(
            property=property_obj, name='Loft', max_adults=2, total_occupancy=2, total_rooms=1
        )
        property_photo = PropertyPhoto.objects.create(
            property=property_obj, cloudinary_url='https://res.cloudinary.com/demo/p.jpg', cloudinary_public_id='p'
        )
        room_photo = RoomTypePhoto.objects.create(
            room_type=room, cloudinary_url='https://res.cloudinary.com/demo/r.jpg', cloudinary_public_id='r'
        )

        response = self.client.delete(f'/api/properties/{property_obj.id}/delete-photo/?photo_id={property_photo.id}')
        self.assertEqual(response.status_code, 200)
        response = self.client.delete(f'/api/properties/rooms/{room.id}/delete-photo/?photo_id={room_photo.id}')
        self.assertEqual(response.status_code, 200)

        self.assertFalse(PropertyPhoto.objects.filter(id=property_photo.id).exists())
        self.assertFalse(RoomTypePhoto.objects.filter(id=room_photo.id).exists())
