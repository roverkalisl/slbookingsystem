"""
Owner Portal: property isolation, editing and the property WhatsApp number.

- GET /api/properties/ is the owner's own list only.
- GET /api/properties/{id}/manage/ (Owner Portal load) answers 404 for any
  property the requester does not own - even an approved, publicly listed one.
- Owners edit their own draft/rejected properties (existing status rule),
  including the WhatsApp number stored on PropertyContact.whatsapp_number.
- Another owner can never read the management view of, or change, them.

Run with: python manage.py test apps.properties.tests_owner_edit_whatsapp
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.models import Role, UserRole
from .models import Amenity, Property, PropertyContact, PropertyPhoto, PropertyType, RoomType

User = get_user_model()
DENIED = (403, 404)


class OwnerEditAndWhatsAppTestCase(APITestCase):
    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner_a = User.objects.create_user(email='edit-owner-a@example.com', password='x')
        self.owner_b = User.objects.create_user(email='edit-owner-b@example.com', password='x')
        for owner in (self.owner_a, self.owner_b):
            UserRole.objects.create(user=owner, role=owner_role)
        self.admin = User.objects.create_superuser(email='edit-admin@example.com', password='x')

        self.hotel = PropertyType.objects.create(name='Edit Hotel')
        self.villa = PropertyType.objects.create(name='Edit Villa')
        self.wifi = Amenity.objects.create(name='Edit WiFi', slug='edit-wifi')
        self.pool = Amenity.objects.create(name='Edit Pool', slug='edit-pool')

        self.prop_a = self.make(self.owner_a, 'Property A', 'draft')
        PropertyContact.objects.create(property=self.prop_a, whatsapp_number='+94 77 123 4567')
        # B is approved: publicly listed, so it is in every owner's *read* queryset
        self.prop_b = self.make(self.owner_b, 'Property B', 'approved')
        PropertyContact.objects.create(property=self.prop_b, whatsapp_number='0719998888')

    def make(self, owner, name, status):
        return Property.objects.create(owner=owner, property_type=self.hotel, name=name, description='d',
                                       address='1 Road', city='Galle', district='Galle', province='Southern',
                                       status=status)

    def as_user(self, user):
        self.client.force_authenticate(user)

    @staticmethod
    def ids(response):
        data = response.data
        rows = data.get('results', data) if isinstance(data, dict) else data
        return {row['id'] for row in rows}

    # 1 + 2
    def test_owner_lists_only_own_properties(self):
        self.as_user(self.owner_a)
        self.assertEqual(self.ids(self.client.get('/api/properties/')), {str(self.prop_a.id)})
        self.as_user(self.owner_b)
        self.assertEqual(self.ids(self.client.get('/api/properties/')), {str(self.prop_b.id)})

    # 3
    def test_owner_cannot_open_another_owners_property_in_owner_portal(self):
        self.as_user(self.owner_a)
        response = self.client.get(f'/api/properties/{self.prop_b.id}/manage/')
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('Property B', str(response.content))
        # The public listing of an approved property stays public, without owner identity
        public = self.client.get(f'/api/properties/{self.prop_b.id}/')
        self.assertEqual(public.status_code, 200)
        self.assertIsNone(public.data['owner_email'])
        # A draft of another owner is not even publicly visible
        self.as_user(self.owner_b)
        self.assertEqual(self.client.get(f'/api/properties/{self.prop_a.id}/').status_code, 404)
        self.assertEqual(self.client.get(f'/api/properties/{self.prop_a.id}/manage/').status_code, 404)

    def test_owner_portal_view_of_own_property(self):
        self.as_user(self.owner_a)
        response = self.client.get(f'/api/properties/{self.prop_a.id}/manage/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Property A')
        self.assertEqual(response.data['property_type_id'], self.hotel.id)
        self.assertEqual(response.data['contact']['whatsapp_number'], '94771234567')

    def test_anonymous_cannot_use_owner_portal_view(self):
        self.assertIn(self.client.get(f'/api/properties/{self.prop_a.id}/manage/').status_code, (401, 403))

    # 4 + 5 + 6 + 7
    def test_owner_cannot_modify_another_owners_property(self):
        self.as_user(self.owner_a)
        self.assertIn(self.client.patch(f'/api/properties/{self.prop_b.id}/', {'name': 'Hacked'}, format='json').status_code, DENIED)
        self.assertIn(self.client.delete(f'/api/properties/{self.prop_b.id}/').status_code, DENIED)
        self.assertIn(self.client.post(f'/api/properties/{self.prop_b.id}/photos/', {
            'cloudinary_url': 'https://res.cloudinary.com/demo/x.jpg', 'cloudinary_public_id': 'x'}, format='json').status_code, DENIED)
        self.assertIn(self.client.post(f'/api/properties/{self.prop_b.id}/rooms/', {
            'name': 'Injected', 'room_type': 'double', 'max_adults': 2, 'max_children': 0,
            'bed_configuration': 'double', 'bathroom_type': 'private', 'number_of_beds': 1, 'total_rooms': 1,
        }, format='json').status_code, DENIED)
        self.prop_b.refresh_from_db()
        self.assertEqual(self.prop_b.name, 'Property B')
        self.assertFalse(PropertyPhoto.objects.filter(property=self.prop_b).exists())
        self.assertFalse(RoomType.objects.filter(property=self.prop_b).exists())

    # 8
    def test_owner_can_edit_own_property_fields(self):
        self.as_user(self.owner_a)
        response = self.client.patch(f'/api/properties/{self.prop_a.id}/', {
            'name': 'Property A Renamed', 'property_type': self.villa.id, 'description': 'New description',
            'short_description': 'Short', 'address': '2 New Road', 'city': 'Unawatuna', 'district': 'Galle',
            'province': 'Southern', 'postal_code': '80600', 'latitude': '6.01000000', 'longitude': '80.25000000',
            'google_maps_url': 'https://maps.google.com/?q=6.01,80.25', 'nearby_attractions': 'Beach 200m',
            'house_rules': 'No smoking', 'contact_phone': '0912223344', 'contact_email': 'a@example.com',
            'amenity_ids': [self.wifi.id, self.pool.id],
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.prop_a.refresh_from_db()
        self.assertEqual(self.prop_a.name, 'Property A Renamed')
        self.assertEqual(self.prop_a.property_type, self.villa)
        self.assertEqual(self.prop_a.city, 'Unawatuna')
        self.assertEqual(self.prop_a.nearby_attractions, 'Beach 200m')
        self.assertEqual(self.prop_a.house_rules, 'No smoking')
        self.assertEqual(set(self.prop_a.amenities.values_list('id', flat=True)), {self.wifi.id, self.pool.id})
        self.assertEqual(self.prop_a.contact.contact_phone, '0912223344')
        self.assertEqual(self.prop_a.contact.email, 'a@example.com')
        self.assertEqual(self.prop_a.owner, self.owner_a)
        self.assertEqual(self.prop_a.status, 'draft')

    def test_rejected_property_is_editable_approved_follows_existing_rule(self):
        Property.objects.filter(pk=self.prop_a.pk).update(status='rejected')
        self.as_user(self.owner_a)
        self.assertEqual(self.client.patch(f'/api/properties/{self.prop_a.id}/', {'name': 'Fixed'}, format='json').status_code, 200)
        # Existing business rule (unchanged): owners cannot edit an approved property
        Property.objects.filter(pk=self.prop_a.pk).update(status='approved')
        self.assertEqual(self.client.patch(f'/api/properties/{self.prop_a.id}/', {'name': 'Nope'}, format='json').status_code, 403)
        self.prop_a.refresh_from_db()
        self.assertEqual(self.prop_a.name, 'Fixed')
        self.assertEqual(self.prop_a.status, 'approved')

    # 9
    def test_owner_can_update_whatsapp_number(self):
        self.as_user(self.owner_a)
        response = self.client.patch(f'/api/properties/{self.prop_a.id}/', {'whatsapp_number': '+94 76 555 4444'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.prop_a.contact.refresh_from_db()
        self.assertEqual(self.prop_a.contact.whatsapp_number, '94765554444')  # normalised digits, not a URL
        manage = self.client.get(f'/api/properties/{self.prop_a.id}/manage/')
        self.assertEqual(manage.data['contact']['whatsapp_number'], '94765554444')

    def test_whatsapp_local_format_blank_and_invalid(self):
        self.as_user(self.owner_a)
        self.client.patch(f'/api/properties/{self.prop_a.id}/', {'whatsapp_number': '077 888 9999'}, format='json')
        self.prop_a.contact.refresh_from_db()
        self.assertEqual(self.prop_a.contact.whatsapp_number, '94778889999')

        bad = self.client.patch(f'/api/properties/{self.prop_a.id}/', {'whatsapp_number': '12ab'}, format='json')
        self.assertEqual(bad.status_code, 400)
        self.assertIn('whatsapp_number', bad.data)
        self.prop_a.contact.refresh_from_db()
        self.assertEqual(self.prop_a.contact.whatsapp_number, '94778889999')

        self.client.patch(f'/api/properties/{self.prop_a.id}/', {'whatsapp_number': ''}, format='json')
        self.prop_a.contact.refresh_from_db()
        self.assertIsNone(self.prop_a.contact.whatsapp_number)

    def test_other_fields_edit_keeps_whatsapp(self):
        self.as_user(self.owner_a)
        self.client.patch(f'/api/properties/{self.prop_a.id}/', {'name': 'Only name'}, format='json')
        self.prop_a.contact.refresh_from_db()
        self.assertEqual(self.prop_a.contact.whatsapp_number, '94771234567')

    def test_owner_can_set_whatsapp_when_creating(self):
        self.as_user(self.owner_a)
        response = self.client.post('/api/properties/', {
            'name': 'New One', 'description': 'd', 'property_type': self.hotel.id, 'address': '3 Rd',
            'city': 'Ella', 'district': 'Badulla', 'province': 'Uva', 'whatsapp_number': '+94701112222',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        created = Property.objects.get(name='New One')
        self.assertEqual(created.owner, self.owner_a)
        self.assertEqual(created.contact.whatsapp_number, '94701112222')

    # 10
    def test_other_owner_cannot_modify_whatsapp_number(self):
        self.as_user(self.owner_b)
        response = self.client.patch(f'/api/properties/{self.prop_a.id}/', {'whatsapp_number': '+94700000000'}, format='json')
        self.assertIn(response.status_code, DENIED)
        # Even when A's property is approved (visible to B), B still cannot change it
        Property.objects.filter(pk=self.prop_a.pk).update(status='approved')
        response = self.client.patch(f'/api/properties/{self.prop_a.id}/', {'whatsapp_number': '+94700000000'}, format='json')
        self.assertIn(response.status_code, DENIED)
        self.prop_a.contact.refresh_from_db()
        self.assertEqual(self.prop_a.contact.whatsapp_number, '94771234567')

    # admin
    def test_admin_manages_both_properties(self):
        self.as_user(self.admin)
        self.assertEqual(self.ids(self.client.get('/api/properties/')), {str(self.prop_a.id), str(self.prop_b.id)})
        for prop in (self.prop_a, self.prop_b):  # B is approved - admins may still edit it
            self.assertEqual(self.client.get(f'/api/properties/{prop.id}/manage/').status_code, 200)
            response = self.client.patch(f'/api/properties/{prop.id}/', {'name': f'Admin {prop.name}',
                                                                           'whatsapp_number': '+94712345678'}, format='json')
            self.assertEqual(response.status_code, 200, response.data)
            prop.refresh_from_db()
            self.assertEqual(prop.name, f'Admin Property {prop.name.split()[-1]}')
            self.assertEqual(prop.contact.whatsapp_number, '94712345678')
