"""
Focused regression tests for the two P0 hotfixes:
1. Guest-facing property search/browse must match status='approved', not 'published'.
2. Room type amenity serialization must not crash (roomtypeamenity_set typo).

Run with: python manage.py test apps.properties.tests_p0_hotfix
"""

from django.test import TestCase
from decimal import Decimal
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model

from .models import Property, PropertyType, RoomType, Amenity, RoomTypeAmenity, PropertyPhoto
from .search import PropertySearchService
from .serializers import RoomTypeListSerializer, RoomTypeDetailSerializer
from apps.core.models import Role, UserRole

User = get_user_model()


class PublishedPropertyFilterTestCase(TestCase):
    """P0 #1: guest search must return approved properties, not 'published' (invalid status)"""

    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='owner-p0@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)

        self.property_type = PropertyType.objects.create(name='Villa P0')

        self.approved_property = Property.objects.create(
            owner=self.owner,
            property_type=self.property_type,
            name='Approved Villa',
            description='desc',
            city='Colombo',
            district='Western',
            province='Western',
            status='approved',
        )

        self.draft_property = Property.objects.create(
            owner=self.owner,
            property_type=self.property_type,
            name='Draft Villa',
            description='desc',
            city='Colombo',
            district='Western',
            province='Western',
            status='draft',
        )

    def test_search_service_default_queryset_returns_approved_only(self):
        """PropertySearchService default queryset must include approved and exclude draft"""
        service = PropertySearchService()
        results = list(service.get_results())

        self.assertIn(self.approved_property, results)
        self.assertNotIn(self.draft_property, results)


class RoomTypeAmenitySerializationTestCase(TestCase):
    """P0 #2: room type serializers must not crash when serializing amenities"""

    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='owner-p0-room@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)

        property_type = PropertyType.objects.create(name='Hotel P0')
        self.property = Property.objects.create(
            owner=self.owner,
            property_type=property_type,
            name='Room Test Property',
            description='desc',
            city='Colombo',
            district='Western',
            province='Western',
            status='approved',
        )

        self.room_type = RoomType.objects.create(
            property=self.property,
            name='Deluxe Room',
            max_adults=2,
            total_occupancy=2,
            total_rooms=1,
        )

        self.wifi = Amenity.objects.create(name='WiFi P0', slug='wifi-p0')
        RoomTypeAmenity.objects.create(room_type=self.room_type, amenity=self.wifi)

    def test_room_type_list_serializer_does_not_crash(self):
        data = RoomTypeListSerializer(self.room_type).data
        self.assertEqual(len(data['amenities']), 1)
        self.assertEqual(data['amenities'][0]['name'], 'WiFi P0')

    def test_room_type_detail_serializer_does_not_crash(self):
        data = RoomTypeDetailSerializer(self.room_type).data
        self.assertEqual(len(data['amenities']), 1)
        self.assertEqual(data['amenities'][0]['name'], 'WiFi P0')


class PropertyWorkflowRegressionTestCase(APITestCase):
    """Property drafts and property photos stay separate from room management."""

    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='owner-p0-workflow@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.property_type = PropertyType.objects.create(name='Villa workflow')
        self.client.force_authenticate(self.owner)

    def test_property_create_does_not_create_rooms(self):
        response = self.client.post('/api/properties/', {
            'property_type': self.property_type.id,
            'name': 'Draft Villa',
            'description': 'A draft property',
            'city': 'Colombo',
            'district': 'Western',
            'province': 'Western',
            'status': 'draft',
            'room_types': [{'name': 'Should not be accepted'}],
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Property.objects.filter(name='Draft Villa').exists())

    def test_sixth_property_photo_is_accepted(self):
        """
        Product requirement change: property photos must support 5+ (10+,
        15+, etc). There is no 5-photo maximum - only a high practical
        ceiling (PropertyViewSet.MAX_PROPERTY_PHOTOS) to prevent abuse.
        """
        property_obj = Property.objects.create(
            owner=self.owner,
            property_type=self.property_type,
            name='Photo villa',
            description='desc',
            city='Colombo',
            district='Western',
            province='Western',
        )
        for index in range(5):
            PropertyPhoto.objects.create(
                property=property_obj,
                cloudinary_url=f'https://example.com/{index}.jpg',
                cloudinary_public_id=f'photo-{index}',
            )

        response = self.client.post(f'/api/properties/{property_obj.id}/photos/', {
            'cloudinary_url': 'https://example.com/6.jpg',
            'cloudinary_public_id': 'photo-6',
        }, format='json')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(property_obj.photos.count(), 6)

    def test_practical_upload_ceiling_still_enforced(self):
        """The abuse-prevention ceiling (not a product limit) still applies."""
        from apps.properties.views import PropertyViewSet

        property_obj = Property.objects.create(
            owner=self.owner,
            property_type=self.property_type,
            name='Photo ceiling villa',
            description='desc',
            city='Colombo',
            district='Western',
            province='Western',
        )
        for index in range(PropertyViewSet.MAX_PROPERTY_PHOTOS):
            PropertyPhoto.objects.create(
                property=property_obj,
                cloudinary_url=f'https://example.com/{index}.jpg',
                cloudinary_public_id=f'photo-{index}',
            )

        response = self.client.post(f'/api/properties/{property_obj.id}/photos/', {
            'cloudinary_url': 'https://example.com/over.jpg',
            'cloudinary_public_id': 'photo-over',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(property_obj.photos.count(), PropertyViewSet.MAX_PROPERTY_PHOTOS)


class PropertyDetailPricingTestCase(APITestCase):
    """
    Property.price_range_min/max don't exist on the model. The property
    detail endpoint must expose a real, database-derived starting price
    (min_price) instead of the frontend silently defaulting to 0.
    """

    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='owner-p0-pricing@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.property_type = PropertyType.objects.create(name='Pricing villa type')

        self.property = Property.objects.create(
            owner=self.owner, property_type=self.property_type, name='Pricing Villa',
            description='desc', city='Colombo', district='Western', province='Western', status='approved',
        )

        from .models import Pricing
        cheap_room = RoomType.objects.create(property=self.property, name='Standard', max_adults=2, total_occupancy=2, total_rooms=2)
        Pricing.objects.create(room_type=cheap_room, base_price='12000.00')
        pricey_room = RoomType.objects.create(property=self.property, name='Suite', max_adults=4, total_occupancy=4, total_rooms=1)
        Pricing.objects.create(room_type=pricey_room, base_price='25000.00')

    def test_property_detail_exposes_real_min_price(self):
        response = self.client.get(f'/api/properties/{self.property.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.data.get('data', response.data)
        self.assertEqual(Decimal(data['min_price']), Decimal('12000.00'))

    def test_room_types_each_expose_their_own_pricing(self):
        """The room picker needs per-room pricing, not just the property minimum."""
        response = self.client.get(f'/api/properties/{self.property.id}/')
        data = response.data.get('data', response.data)
        prices = sorted(Decimal(rt['pricing']['base_price']) for rt in data['room_types'])
        self.assertEqual(prices, [Decimal('12000.00'), Decimal('25000.00')])


class PropertyApprovalNotificationTestCase(APITestCase):
    """P1: owner notifications for property approved/rejected must actually fire."""

    def setUp(self):
        from django.core import mail
        mail.outbox = []
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.owner = User.objects.create_user(email='approval-owner@example.com', password='test')
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.admin = User.objects.create_user(email='approval-admin@example.com', password='test', is_staff=True)
        property_type = PropertyType.objects.create(name='Approval villa type')
        self.property = Property.objects.create(
            owner=self.owner, property_type=property_type, name='Approval Villa',
            description='desc', city='Colombo', district='Western', province='Western',
            status='pending_approval',
        )

    def test_approve_sends_notification_and_email(self):
        from django.core import mail
        from apps.notifications.models import Notification

        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/api/properties/{self.property.id}/approve/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Notification.objects.filter(recipient=self.owner, notification_type='property_approved').exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.owner.email, mail.outbox[0].to)

    def test_reject_sends_notification_and_email(self):
        from django.core import mail
        from apps.notifications.models import Notification

        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/api/properties/{self.property.id}/reject/', {'rejection_reason': 'Missing photos'}, format='json')

        self.assertEqual(response.status_code, 200)
        notification = Notification.objects.filter(recipient=self.owner, notification_type='property_rejected').first()
        self.assertIsNotNone(notification)
        self.assertIn('Missing photos', notification.message)
        self.assertEqual(len(mail.outbox), 1)
