"""
Focused regression tests for the two P0 hotfixes:
1. Guest-facing property search/browse must match status='approved', not 'published'.
2. Room type amenity serialization must not crash (roomtypeamenity_set typo).

Run with: python manage.py test apps.properties.tests_p0_hotfix
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import Property, PropertyType, RoomType, Amenity, RoomTypeAmenity
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
