"""
Regression tests for the admin approval queue blocker.

Root cause: the admin queue (and the dashboard's pending list) loaded
properties from the GUEST search endpoint /api/properties/search/advanced/,
which only ever returns approved properties - so a property an owner had just
submitted (status 'pending_approval') could never appear. The admin pages now
use GET /api/properties/ (staff see every status, filterable by ?status=).

Run with: python manage.py test apps.properties.tests_admin_queue
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.models import Role, UserRole
from .models import Property, PropertyPhoto, PropertyType, RoomType, RoomTypePhoto, Pricing

User = get_user_model()
QUEUE_URL = '/api/properties/'
DASHBOARD_URL = '/api/admin/stats/dashboard/'


class AdminQueueTestBase(APITestCase):
    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner_a = User.objects.create_user(email='queue-owner-a@example.com', password='test',
                                                first_name='Asha', last_name='Owner')
        UserRole.objects.create(user=self.owner_a, role=owner_role)
        self.owner_b = User.objects.create_user(email='queue-owner-b@example.com', password='test')
        UserRole.objects.create(user=self.owner_b, role=owner_role)
        self.admin = User.objects.create_user(email='queue-admin@example.com', password='test', is_staff=True)
        self.property_type = PropertyType.objects.create(name='Queue Villa Type')

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return self.client

    def photo(self, label):
        return {'cloudinary_url': f'https://res.cloudinary.com/demo/{label}.jpg', 'cloudinary_public_id': label}

    def create_and_submit(self, owner, name):
        """Owner creates a draft, completes it through the API, and submits it."""
        client = self.as_user(owner)
        r = client.post('/api/properties/', {
            'name': name, 'property_type': self.property_type.id, 'description': 'Desc',
            'address': '1 Road', 'city': 'Kandy', 'district': 'Kandy', 'province': 'Central', 'status': 'draft',
        }, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        property_id = r.data.get('data', r.data)['id']
        for i in range(5):
            client.post(f'/api/properties/{property_id}/photos/', self.photo(f'{name}-p{i}'), format='json')
        room = client.post(f'/api/properties/{property_id}/rooms/', {
            'name': 'Room', 'max_adults': 2, 'max_children': 0, 'total_rooms': 1, 'number_of_beds': 1,
        }, format='json').data['data']
        for i in range(5):
            client.post(f'/api/properties/rooms/{room["id"]}/add-photo/', self.photo(f'{name}-r{i}'), format='json')
        client.post(f'/api/properties/rooms/{room["id"]}/pricing/', {'base_price': '9000.00'}, format='json')
        r = client.post(f'/api/properties/{property_id}/submit-for-approval/')
        self.assertEqual(r.status_code, 200, r.data)
        return property_id

    def queue(self, **params):
        """Collect every page exactly like frontend api.getAdminProperties()."""
        client = self.as_user(self.admin)
        items, page = [], 1
        while True:
            r = client.get(QUEUE_URL, {'page': page, 'ordering': '-created_at', **params})
            self.assertEqual(r.status_code, 200, r.data)
            items += r.data['results']
            if not r.data['next']:
                return items
            page += 1

    def pending_count(self):
        r = self.as_user(self.admin).get(DASHBOARD_URL)
        self.assertEqual(r.status_code, 200)
        return r.data['data']['pending_properties']


class AdminQueueWorkflowTestCase(AdminQueueTestBase):

    def test_submitted_property_reaches_admin_queue_and_can_be_approved(self):
        owner = self.as_user(self.owner_a)

        # 1-2. Owner creates an incomplete draft - submission is refused
        r = owner.post('/api/properties/', {
            'name': 'Queue Villa', 'property_type': self.property_type.id, 'description': 'Desc',
            'address': '1 Road', 'city': 'Kandy', 'district': 'Kandy', 'province': 'Central', 'status': 'draft',
        }, format='json')
        property_id = r.data.get('data', r.data)['id']
        self.assertEqual(owner.post(f'/api/properties/{property_id}/submit-for-approval/').status_code, 400)
        self.assertNotIn(property_id, [p['id'] for p in self.queue(status='pending_approval')])
        self.assertEqual(self.pending_count(), 0)

        # 3-5. Owner completes the property and submits it
        owner = self.as_user(self.owner_a)
        for i in range(5):
            owner.post(f'/api/properties/{property_id}/photos/', self.photo(f'p{i}'), format='json')
        room = owner.post(f'/api/properties/{property_id}/rooms/', {
            'name': 'Garden Room', 'max_adults': 2, 'max_children': 0, 'total_rooms': 1, 'number_of_beds': 1,
        }, format='json').data['data']
        for i in range(5):
            owner.post(f'/api/properties/rooms/{room["id"]}/add-photo/', self.photo(f'r{i}'), format='json')
        owner.post(f'/api/properties/rooms/{room["id"]}/pricing/', {'base_price': '9000.00'}, format='json')
        self.assertEqual(owner.post(f'/api/properties/{property_id}/submit-for-approval/').status_code, 200)
        self.assertEqual(Property.objects.get(id=property_id).status, 'pending_approval')

        # 6. Admin queue returns it (with owner details for review)
        pending = self.queue(status='pending_approval')
        entry = next(p for p in pending if p['id'] == property_id)
        self.assertEqual(entry['status'], 'pending_approval')
        self.assertEqual(entry['owner_info']['email'], 'queue-owner-a@example.com')
        self.assertIn(property_id, [p['id'] for p in self.queue()])  # also in the unfiltered "all" view

        # 10. Dashboard pending count includes it
        self.assertEqual(self.pending_count(), 1)

        # 7. Admin can open it with photos, rooms, room photos and pricing
        detail = self.as_user(self.admin).get(f'/api/properties/{property_id}/').data
        detail = detail.get('data', detail)
        self.assertEqual(len(detail['photos']), 5)
        self.assertEqual(len(detail['room_types']), 1)
        self.assertEqual(len(detail['room_types'][0]['photos']), 5)
        self.assertEqual(Decimal(str(detail['room_types'][0]['pricing']['base_price'])), Decimal('9000.00'))

        # 9. Owner cannot approve or reject their own property
        owner = self.as_user(self.owner_a)
        self.assertEqual(owner.post(f'/api/properties/{property_id}/approve/').status_code, 403)
        self.assertEqual(owner.post(f'/api/properties/{property_id}/reject/', {'rejection_reason': 'x'}, format='json').status_code, 403)

        # 8. Admin approves it - it leaves the pending queue
        self.assertEqual(self.as_user(self.admin).post(f'/api/properties/{property_id}/approve/').status_code, 200)
        self.assertEqual(Property.objects.get(id=property_id).status, 'approved')
        self.assertNotIn(property_id, [p['id'] for p in self.queue(status='pending_approval')])
        self.assertEqual(self.pending_count(), 0)

    def test_admin_can_reject_from_queue(self):
        property_id = self.create_and_submit(self.owner_a, 'Reject Villa')
        self.assertIn(property_id, [p['id'] for p in self.queue(status='pending_approval')])
        r = self.as_user(self.admin).post(f'/api/properties/{property_id}/reject/', {'rejection_reason': 'Blurry photos'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Property.objects.get(id=property_id).status, 'rejected')
        self.assertNotIn(property_id, [p['id'] for p in self.queue(status='pending_approval')])

    def test_pending_properties_from_multiple_owners_all_appear(self):
        a = self.create_and_submit(self.owner_a, 'Owner A Villa')
        b = self.create_and_submit(self.owner_b, 'Owner B Villa')
        pending = {p['id']: p for p in self.queue(status='pending_approval')}
        self.assertIn(a, pending)
        self.assertIn(b, pending)
        self.assertEqual(pending[a]['owner_info']['email'], 'queue-owner-a@example.com')
        self.assertEqual(pending[b]['owner_info']['email'], 'queue-owner-b@example.com')
        self.assertEqual(self.pending_count(), 2)

    def test_root_cause_guest_search_endpoint_never_returns_pending(self):
        """Documents why the old queue failed: the search endpoint is approved-only."""
        property_id = self.create_and_submit(self.owner_a, 'Hidden From Search')
        r = self.as_user(self.admin).get('/api/properties/search/advanced/')
        self.assertNotIn(property_id, [str(p['id']) for p in r.data.get('results', [])])


class AdminQueuePaginationTestCase(AdminQueueTestBase):

    def test_pagination_never_hides_pending_properties(self):
        # 24 pending (more than one 20-item page) + the newest one via the real flow
        for i in range(24):
            Property.objects.create(
                owner=self.owner_b if i % 2 else self.owner_a, property_type=self.property_type,
                name=f'Bulk Pending {i}', description='d', city='Galle', district='Galle', province='Southern',
                status='pending_approval',
            )
        newest = self.create_and_submit(self.owner_a, 'Newest Submitted')

        first_page = self.as_user(self.admin).get(QUEUE_URL, {'status': 'pending_approval', 'ordering': '-created_at'}).data
        self.assertEqual(first_page['count'], 25)
        self.assertEqual(len(first_page['results']), 20)
        self.assertIsNotNone(first_page['next'])

        all_pending = self.queue(status='pending_approval')
        ids = [p['id'] for p in all_pending]
        self.assertEqual(len(ids), 25)
        self.assertEqual(len(set(ids)), 25)  # stable ordering - no duplicates or gaps across pages
        self.assertIn(newest, ids)
        self.assertEqual(self.pending_count(), 25)


class OwnerInfoPrivacyTestCase(AdminQueueTestBase):

    def test_owner_info_is_staff_only(self):
        property_id = self.create_and_submit(self.owner_a, 'Private Villa')
        self.as_user(self.admin).post(f'/api/properties/{property_id}/approve/')

        # Anonymous users see approved properties, but never owner contact details
        self.client.force_authenticate(user=None)
        public = next(p for p in self.client.get(QUEUE_URL).data['results'] if p['id'] == property_id)
        self.assertIsNone(public['owner_info'])
        # Another owner's list is their own "My Properties" - owner A's listing is not in it at all
        other_ids = [p['id'] for p in self.as_user(self.owner_b).get(QUEUE_URL).data['results']]
        self.assertNotIn(property_id, other_ids)

    def test_non_staff_cannot_see_other_owners_pending_properties(self):
        property_id = self.create_and_submit(self.owner_a, 'Owner A Pending')
        r = self.as_user(self.owner_b).get(QUEUE_URL, {'status': 'pending_approval'})
        self.assertNotIn(property_id, [p['id'] for p in r.data['results']])
        self.client.force_authenticate(user=None)
        self.assertNotIn(property_id, [p['id'] for p in self.client.get(QUEUE_URL).data['results']])
