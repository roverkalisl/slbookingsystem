"""
Only property owners (and admins) may create properties.

POST /api/properties/ is refused with 403 for guests (whatever they put in
the payload) and 401/403 for anonymous users; the owner of a new property is
always the logged-in user, never an id from the request.

Run with: python manage.py test apps.properties.tests_create_permission
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.models import Role, UserRole
from .models import Property, PropertyType

User = get_user_model()
URL = '/api/properties/'


class PropertyCreatePermissionTestCase(APITestCase):
    def setUp(self):
        self.guest_role, _ = Role.objects.get_or_create(name='guest')
        self.owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.admin_role, _ = Role.objects.get_or_create(name='super_admin')

        self.guest = self.user('create-guest@example.com', self.guest_role)
        self.owner = self.user('create-owner@example.com', self.owner_role)
        self.other_owner = self.user('create-other-owner@example.com', self.owner_role)
        self.no_role = self.user('create-norole@example.com')
        self.staff = User.objects.create_user(email='create-staff@example.com', password='x', is_staff=True)
        self.superuser = User.objects.create_superuser(email='create-super@example.com', password='x')
        self.role_admin = self.user('create-roleadmin@example.com', self.admin_role)
        self.hotel = PropertyType.objects.create(name='Create Test Hotel')

    @staticmethod
    def user(email, role=None):
        user = User.objects.create_user(email=email, password='x')
        if role:
            UserRole.objects.create(user=user, role=role)
        return user

    def payload(self, **extra):
        return {'name': 'New Listing', 'description': 'A place', 'property_type': self.hotel.id,
                'address': '1 Beach Rd', 'city': 'Mirissa', 'district': 'Matara', 'province': 'Southern', **extra}

    def post_as(self, actor, **extra):
        self.client.force_authenticate(actor)
        return self.client.post(URL, self.payload(**extra), format='json')

    # --- guest ---

    def test_guest_gets_403_and_nothing_is_created(self):
        response = self.post_as(self.guest)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Property.objects.exists())

    def test_guest_cannot_bypass_with_payload_tricks(self):
        tricks = [
            {'owner': str(self.owner.id)},
            {'owner_id': str(self.owner.id), 'user': str(self.owner.id), 'user_id': str(self.owner.id)},
            {'role': 'property_owner', 'roles': ['property_owner', 'super_admin']},
            {'is_staff': True, 'is_superuser': True, 'is_admin': True},
            {'status': 'approved'},
        ]
        for extra in tricks:
            self.assertEqual(self.post_as(self.guest, **extra).status_code, 403, extra)
        # Query-string / form-encoded variants
        self.client.force_authenticate(self.guest)
        self.assertEqual(self.client.post(f'{URL}?role=property_owner&owner={self.owner.id}', self.payload()).status_code, 403)
        self.assertFalse(Property.objects.exists())

    def test_guest_cannot_become_owner_through_profile_update(self):
        self.client.force_authenticate(self.guest)
        self.client.patch('/api/auth/update-profile/', {'roles': ['property_owner'], 'is_staff': True,
                                                         'is_superuser': True}, format='json')
        self.guest.refresh_from_db()
        self.assertFalse(self.guest.has_role('property_owner'))
        self.assertFalse(self.guest.is_staff or self.guest.is_superuser)
        self.assertEqual(self.post_as(self.guest).status_code, 403)

    def test_user_without_any_role_cannot_create(self):
        self.assertEqual(self.post_as(self.no_role).status_code, 403)

    # --- anonymous ---

    def test_anonymous_cannot_create(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.post(URL, self.payload(), format='json').status_code, (401, 403))
        self.assertFalse(Property.objects.exists())

    # --- property owner ---

    def test_owner_can_create_and_is_assigned_as_owner(self):
        response = self.post_as(self.owner)
        self.assertEqual(response.status_code, 201, response.data)
        prop = Property.objects.get()
        self.assertEqual(prop.owner, self.owner)
        self.assertEqual(prop.status, 'draft')

    def test_owner_cannot_create_a_property_for_someone_else(self):
        response = self.post_as(self.owner, owner=str(self.other_owner.id), owner_id=str(self.other_owner.id),
                                user=str(self.other_owner.id), status='approved')
        self.assertEqual(response.status_code, 201, response.data)
        prop = Property.objects.get()
        self.assertEqual(prop.owner, self.owner)
        self.assertEqual(prop.status, 'draft')
        self.assertFalse(Property.objects.filter(owner=self.other_owner).exists())

    # --- admins ---

    def test_admins_can_still_create_and_manage(self):
        for admin in (self.staff, self.superuser, self.role_admin):
            response = self.post_as(admin, name=f'Admin {admin.email}')
            self.assertEqual(response.status_code, 201, (admin.email, response.data))
            prop = Property.objects.get(name=f'Admin {admin.email}')
            self.assertEqual(prop.owner, admin)
        # Existing admin management of an owner's property is unchanged
        owner_prop = Property.objects.create(owner=self.owner, property_type=self.hotel, name='Owner Place',
                                             description='d', city='Ella', district='Badulla', province='Uva')
        self.client.force_authenticate(self.superuser)
        self.assertEqual(self.client.patch(f'{URL}{owner_prop.id}/', {'name': 'Edited by admin'}, format='json').status_code, 200)

    # --- other actions unaffected ---

    def test_guest_can_still_browse_properties(self):
        Property.objects.create(owner=self.owner, property_type=self.hotel, name='Public', description='d',
                                city='Ella', district='Badulla', province='Uva', status='approved')
        self.client.force_authenticate(self.guest)
        self.assertEqual(self.client.get(URL).status_code, 200)
