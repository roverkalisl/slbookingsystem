"""
Property cover photo: exactly one PropertyPhoto per property is the cover
(is_cover, DB-enforced); owners/admins change it with
POST /api/properties/{id}/set-cover/, deleting the cover promotes the first
remaining photo, and every property response exposes cover_photo_url.

Run with: python manage.py test apps.properties.tests_cover_photo
"""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from apps.core.models import Role, UserRole
from .models import Property, PropertyPhoto, PropertyType

User = get_user_model()


class CoverPhotoTestCase(APITestCase):
    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='cover-owner@example.com', password='test')
        self.other_owner = User.objects.create_user(email='cover-other@example.com', password='test')
        for user in (self.owner, self.other_owner):
            UserRole.objects.create(user=user, role=owner_role)
        self.admin = User.objects.create_user(email='cover-admin@example.com', password='test', is_staff=True)

        hotel = PropertyType.objects.create(name='Cover Hotel Type')
        self.prop = self.make_property(self.owner, 'Cover Villa', hotel)
        self.other_prop = self.make_property(self.other_owner, 'Other Villa', hotel)
        self.client.force_authenticate(self.owner)

    @staticmethod
    def make_property(owner, name, property_type):
        return Property.objects.create(owner=owner, property_type=property_type, name=name, description='d',
                                       city='Ella', district='Badulla', province='Uva', status='draft')

    def upload(self, prop, name):
        """Add a photo through the real API (the flow the owner UI uses)."""
        response = self.client.post(f'/api/properties/{prop.id}/photos/', {
            'cloudinary_url': f'https://res.cloudinary.com/demo/{name}.jpg',
            'cloudinary_public_id': f'slbooking/properties/{name}',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return PropertyPhoto.objects.get(id=response.data['data']['id'])

    def set_cover(self, prop, photo_id):
        return self.client.post(f'/api/properties/{prop.id}/set-cover/', {'photo_id': str(photo_id)}, format='json')

    def covers(self, prop):
        return list(PropertyPhoto.objects.filter(property=prop, is_cover=True))

    # --- one cover per property ---

    def test_first_upload_becomes_the_only_cover(self):
        first = self.upload(self.prop, 'a')
        self.upload(self.prop, 'b')
        self.upload(self.prop, 'c')
        self.assertEqual(self.covers(self.prop), [first])
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.cover_photo_url, first.cloudinary_url)

    def test_database_rejects_a_second_cover(self):
        self.upload(self.prop, 'a')
        second = self.upload(self.prop, 'b')
        second.is_cover = True
        with self.assertRaises(IntegrityError), transaction.atomic():
            second.save()

    # --- set cover ---

    def test_set_cover_replaces_the_previous_cover(self):
        first = self.upload(self.prop, 'a')
        second = self.upload(self.prop, 'b')
        response = self.set_cover(self.prop, second.id)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.covers(self.prop), [second])
        first.refresh_from_db()
        self.assertFalse(first.is_cover)
        self.assertEqual(response.data['data']['cover_photo_url'], second.cloudinary_url)
        self.assertEqual(len(response.data['data']['photos']), 2)
        self.assertEqual(PropertyPhoto.objects.filter(property=self.prop).count(), 2)  # no duplicate row
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.cover_photo_url, second.cloudinary_url)

    def test_setting_the_current_cover_again_is_harmless(self):
        first = self.upload(self.prop, 'a')
        self.assertEqual(self.set_cover(self.prop, first.id).status_code, 200)
        self.assertEqual(self.covers(self.prop), [first])

    def test_cannot_set_another_propertys_photo_as_cover(self):
        mine = self.upload(self.prop, 'mine')
        self.client.force_authenticate(self.other_owner)
        foreign = self.upload(self.other_prop, 'foreign')
        self.client.force_authenticate(self.owner)

        response = self.set_cover(self.prop, foreign.id)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.covers(self.prop), [mine])
        foreign.refresh_from_db()
        self.assertEqual(foreign.property_id, self.other_prop.id)

    def test_owner_cannot_change_another_owners_cover(self):
        self.client.force_authenticate(self.other_owner)
        self.upload(self.other_prop, 'x')
        second = self.upload(self.other_prop, 'y')
        # Approved so it is visible to the attacker (draft would already be a 404)
        Property.objects.filter(pk=self.other_prop.pk).update(status='approved')

        self.client.force_authenticate(self.owner)
        self.assertEqual(self.set_cover(self.other_prop, second.id).status_code, 403)
        second.refresh_from_db()
        self.assertFalse(second.is_cover)

    def test_admin_can_change_any_propertys_cover(self):
        self.upload(self.prop, 'a')
        second = self.upload(self.prop, 'b')
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.set_cover(self.prop, second.id).status_code, 200)
        self.assertEqual(self.covers(self.prop), [second])

    def test_anonymous_cannot_set_cover(self):
        photo = self.upload(self.prop, 'a')
        self.client.force_authenticate(None)
        self.assertIn(self.set_cover(self.prop, photo.id).status_code, (401, 403))

    def test_missing_or_malformed_photo_id(self):
        self.upload(self.prop, 'a')
        self.assertEqual(self.client.post(f'/api/properties/{self.prop.id}/set-cover/', {}, format='json').status_code, 400)
        self.assertEqual(self.set_cover(self.prop, 'not-a-uuid').status_code, 404)

    # --- delete ---

    def test_deleting_the_cover_promotes_the_first_remaining_photo(self):
        first = self.upload(self.prop, 'a')
        second = self.upload(self.prop, 'b')
        self.upload(self.prop, 'c')
        response = self.client.delete(f'/api/properties/{self.prop.id}/delete-photo/?photo_id={first.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.covers(self.prop), [second])
        self.assertEqual(response.data['data']['cover_photo_url'], second.cloudinary_url)

    def test_deleting_a_normal_photo_keeps_the_cover(self):
        first = self.upload(self.prop, 'a')
        second = self.upload(self.prop, 'b')
        self.client.delete(f'/api/properties/{self.prop.id}/delete-photo/?photo_id={second.id}')
        self.assertEqual(self.covers(self.prop), [first])

    def test_deleting_the_final_photo_makes_cover_null(self):
        only = self.upload(self.prop, 'a')
        response = self.client.delete(f'/api/properties/{self.prop.id}/delete-photo/?photo_id={only.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['data']['cover_photo_url'])
        self.prop.refresh_from_db()
        self.assertIsNone(self.prop.cover_photo_url)
        self.assertIsNone(self.client.get(f'/api/properties/{self.prop.id}/').data['cover_photo_url'])

    # --- serializers ---

    def test_detail_returns_cover_photo_url_and_photos(self):
        self.upload(self.prop, 'a')
        second = self.upload(self.prop, 'b')
        self.set_cover(self.prop, second.id)
        data = self.client.get(f'/api/properties/{self.prop.id}/').data
        self.assertEqual(data['cover_photo_url'], second.cloudinary_url)
        self.assertEqual(len(data['photos']), 2)
        self.assertEqual([p['is_cover'] for p in data['photos']].count(True), 1)

    def test_search_card_uses_the_chosen_cover(self):
        self.upload(self.prop, 'a')
        second = self.upload(self.prop, 'b')
        self.set_cover(self.prop, second.id)
        Property.objects.filter(pk=self.prop.pk).update(status='approved')
        data = self.client.get('/api/properties/search/featured/').data
        results = data.get('data', data) if isinstance(data, dict) else data
        if isinstance(results, dict):
            results = results.get('results', [])
        card = next(p for p in results if p['name'] == 'Cover Villa')
        self.assertEqual(card['cover_photo_url'], second.cloudinary_url)

    def test_cover_photo_url_cannot_be_written_directly(self):
        photo = self.upload(self.prop, 'a')
        response = self.client.patch(f'/api/properties/{self.prop.id}/',
                                      {'cover_photo_url': 'https://evil.example.com/x.jpg'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.cover_photo_url, photo.cloudinary_url)
