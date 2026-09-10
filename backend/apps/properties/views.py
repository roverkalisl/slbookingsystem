"""
Views for property management.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import (
    PropertyType, Amenity, Destination, Property, PropertyPhoto,
    RoomType, RoomTypePhoto, Pricing, SeasonalRate
)
from .serializers import (
    PropertyTypeSerializer, AmenitySerializer, DestinationSerializer,
    PropertyListSerializer, PropertyDetailSerializer,
    PropertyCreateUpdateSerializer, PropertyApprovalSerializer,
    RoomTypeListSerializer, RoomTypeDetailSerializer,
    PropertyPhotoSerializer, RoomTypePhotoSerializer,
    PricingSerializer, SeasonalRateSerializer
)
from .pricing import PricingCalculator


class PropertyTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for property types (read-only for guests)"""
    queryset = PropertyType.objects.filter(is_active=True)
    serializer_class = PropertyTypeSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class AmenityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for amenities (read-only for guests)"""
    queryset = Amenity.objects.filter(is_active=True)
    serializer_class = AmenitySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'category']
    ordering_fields = ['category', 'name']


class DestinationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for destinations (read-only for guests)"""
    queryset = Destination.objects.filter(is_published=True)
    serializer_class = DestinationSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'city', 'district']
    ordering_fields = ['name', 'city']


class PropertyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for properties.

    Permissions:
    - Any user can view published properties
    - Authenticated users can create properties
    - Only property owner can edit own property
    - Only super admin can approve/reject properties
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['city', 'district', 'property_type', 'status']
    search_fields = ['name', 'description', 'city']
    ordering_fields = ['created_at', 'average_rating', 'name']

    def get_queryset(self):
        """Get appropriate queryset based on user"""
        user = self.request.user

        # Unauthenticated users see published properties only
        if not user.is_authenticated:
            return Property.objects.filter(status='published')

        # Guests see published properties
        if user.has_role('guest'):
            return Property.objects.filter(status='published')

        # Property owners see their own properties + published
        if user.has_role('property_owner'):
            return Property.objects.filter(
                owner=user
            ) | Property.objects.filter(status='published')

        # Super admin sees everything
        if user.is_staff:
            return Property.objects.all()

        return Property.objects.filter(status='published')

    def get_serializer_class(self):
        """Choose serializer based on action"""
        if self.action == 'retrieve':
            return PropertyDetailSerializer
        elif self.action == 'list':
            return PropertyListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PropertyCreateUpdateSerializer
        return PropertyDetailSerializer

    def perform_create(self, serializer):
        """Create property with current user as owner"""
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        """Update property (only owner can update)"""
        property_obj = self.get_object()
        if property_obj.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only edit your own properties.")
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """
        Approve a property (admin only).

        POST /api/properties/{id}/approve/
        """
        property_obj = self.get_object()

        if property_obj.status == 'published':
            return Response(
                {'error': 'Property is already published'},
                status=status.HTTP_400_BAD_REQUEST
            )

        property_obj.status = 'published'
        property_obj.published_at = now()
        property_obj.save()

        return Response(
            {
                'success': True,
                'message': 'Property approved and published',
                'data': PropertyDetailSerializer(property_obj).data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def reject(self, request, pk=None):
        """
        Reject a property (admin only).

        POST /api/properties/{id}/reject/
        {
            "reason": "Description does not meet guidelines"
        }
        """
        property_obj = self.get_object()
        reason = request.data.get('reason', 'No reason provided')

        property_obj.status = 'rejected'
        property_obj.save()

        # TODO: Send email to owner with rejection reason

        return Response(
            {
                'success': True,
                'message': 'Property rejected',
                'reason': reason
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def suspend(self, request, pk=None):
        """
        Suspend a property (admin only).

        POST /api/properties/{id}/suspend/
        {
            "reason": "Violation of terms"
        }
        """
        property_obj = self.get_object()
        reason = request.data.get('reason', 'No reason provided')

        property_obj.status = 'suspended'
        property_obj.save()

        # TODO: Send email to owner with suspension reason

        return Response(
            {
                'success': True,
                'message': 'Property suspended',
                'reason': reason
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def photos(self, request, pk=None):
        """
        Get all photos for a property.

        GET /api/properties/{id}/photos/
        """
        property_obj = self.get_object()
        photos = property_obj.photos.all().order_by('display_order')
        serializer = PropertyPhotoSerializer(photos, many=True)
        return Response(
            {
                'success': True,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get'])
    def rooms(self, request, pk=None):
        """
        Get all room types for a property.

        GET /api/properties/{id}/rooms/
        """
        property_obj = self.get_object()
        rooms = property_obj.room_types.all()
        serializer = RoomTypeListSerializer(rooms, many=True)
        return Response(
            {
                'success': True,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )


class RoomTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for room types"""

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = RoomTypeDetailSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['property', 'is_active']

    def get_queryset(self):
        """Get room types from published properties or user's own properties"""
        user = self.request.user

        if not user.is_authenticated:
            return RoomType.objects.filter(
                property__status='published',
                is_active=True
            )

        if user.has_role('property_owner'):
            return RoomType.objects.filter(
                property__owner=user
            ) | RoomType.objects.filter(property__status='published')

        if user.is_staff:
            return RoomType.objects.all()

        return RoomType.objects.filter(
            property__status='published',
            is_active=True
        )

    def perform_create(self, serializer):
        """Create room type"""
        property_obj = serializer.validated_data['property']

        # Check ownership
        if property_obj.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only add rooms to your own properties.")

        serializer.save()

    def perform_update(self, serializer):
        """Update room type"""
        room_type = self.get_object()

        # Check ownership
        if room_type.property.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only edit rooms in your own properties.")

        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_photo(self, request, pk=None):
        """
        Add a photo to room type (currently expects Cloudinary URL in body).

        POST /api/properties/rooms/{id}/add-photo/
        {
            "cloudinary_url": "https://res.cloudinary.com/...",
            "cloudinary_public_id": "slbooking/property123/room456",
            "is_cover": false,
            "display_order": 1
        }
        """
        room_type = self.get_object()

        # Check ownership
        if room_type.property.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You can only add photos to your own rooms.")

        cloudinary_url = request.data.get('cloudinary_url')
        cloudinary_public_id = request.data.get('cloudinary_public_id')
        is_cover = request.data.get('is_cover', False)
        display_order = request.data.get('display_order', 0)

        if not cloudinary_url or not cloudinary_public_id:
            return Response(
                {'error': 'cloudinary_url and cloudinary_public_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        photo = RoomTypePhoto.objects.create(
            room_type=room_type,
            cloudinary_url=cloudinary_url,
            cloudinary_public_id=cloudinary_public_id,
            is_cover=is_cover,
            display_order=display_order
        )

        return Response(
            {
                'success': True,
                'message': 'Photo added successfully',
                'data': RoomTypePhotoSerializer(photo).data
            },
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['get', 'post'], permission_classes=[permissions.IsAuthenticated])
    def pricing(self, request, pk=None):
        """
        Get or update pricing for a room type.

        GET /api/properties/rooms/{id}/pricing/
        POST /api/properties/rooms/{id}/pricing/
        {
            "base_price": "5000.00",
            "weekend_price": "6000.00",
            "extra_guest_fee": "1000.00",
            "child_fee": "500.00"
        }
        """
        room_type = self.get_object()

        if request.method == 'GET':
            try:
                pricing = Pricing.objects.get(room_type=room_type)
            except Pricing.DoesNotExist:
                return Response(
                    {'error': 'Pricing not configured for this room'},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = PricingSerializer(pricing)
            return Response(
                {
                    'success': True,
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )

        elif request.method == 'POST':
            # Check ownership
            if room_type.property.owner != request.user and not request.user.is_staff:
                raise PermissionDenied("You can only update pricing for your own rooms.")

            # Get or create pricing
            pricing, created = Pricing.objects.get_or_create(room_type=room_type)

            # Update fields
            if 'base_price' in request.data:
                pricing.base_price = request.data['base_price']
            if 'weekend_price' in request.data:
                pricing.weekend_price = request.data.get('weekend_price') or None
            if 'extra_guest_fee' in request.data:
                pricing.extra_guest_fee = request.data.get('extra_guest_fee') or None
            if 'child_fee' in request.data:
                pricing.child_fee = request.data.get('child_fee') or None

            pricing.save()

            serializer = PricingSerializer(pricing)
            return Response(
                {
                    'success': True,
                    'message': 'Pricing updated successfully',
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def calculate_price(self, request, pk=None):
        """
        Calculate price for a booking.

        GET /api/properties/rooms/{id}/calculate-price/?check_in=2026-09-15&check_out=2026-09-17&adults=2&children=0

        Query Parameters:
        - check_in: Check-in date (YYYY-MM-DD)
        - check_out: Check-out date (YYYY-MM-DD)
        - adults: Number of adults
        - children: Number of children
        - discount_percent: Discount percentage (optional)
        - discount_fixed: Fixed discount amount (optional)
        """
        room_type = self.get_object()

        try:
            check_in_str = request.query_params.get('check_in')
            check_out_str = request.query_params.get('check_out')
            adults = int(request.query_params.get('adults', 1))
            children = int(request.query_params.get('children', 0))
            discount_percent = request.query_params.get('discount_percent', 0)
            discount_fixed = request.query_params.get('discount_fixed', 0)

            from datetime import datetime
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()

            # Calculate price
            calculator = PricingCalculator(room_type)
            price_breakdown = calculator.calculate_booking_price(
                check_in, check_out,
                num_adults=adults,
                num_children=children,
                discount_percent=discount_percent,
                discount_fixed=discount_fixed
            )

            return Response(
                {
                    'success': True,
                    'data': price_breakdown
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
