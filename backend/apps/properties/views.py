"""
Views for property management.
"""

import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

logger = logging.getLogger(__name__)

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
    PricingSerializer, SeasonalRateSerializer,
    PropertyCardSerializer, SearchFilterSerializer,
    DestinationDetailSerializer, SearchResultsSerializer
)
from .pricing import PricingCalculator
from .search import PropertySearchService, DestinationSearchService, SearchFilters


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

        # Unauthenticated users see approved properties only
        if not user.is_authenticated:
            return Property.objects.filter(status='approved')

        # Guests see approved properties only
        if user.has_role('guest'):
            return Property.objects.filter(status='approved')

        # Property owners see:
        # - Their own properties (all statuses)
        # - Other owners' approved properties
        if user.has_role('property_owner'):
            return Property.objects.filter(
                owner=user
            ) | Property.objects.filter(status='approved')

        # Super admin sees everything
        if user.is_staff:
            return Property.objects.all()

        # Default: show only approved properties
        return Property.objects.filter(status='approved')

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
        logger.info(f"Creating property for user {self.request.user.email if self.request.user else 'anonymous'}")
        logger.debug(f"Serializer data: {serializer.validated_data}")
        try:
            serializer.save(owner=self.request.user)
            logger.info(f"Property created successfully: {serializer.instance.id}")
        except Exception as e:
            logger.error(f"Error creating property: {str(e)}", exc_info=True)
            raise

    def perform_update(self, serializer):
        """Update property (only owner can update DRAFT/REJECTED properties)"""
        property_obj = self.get_object()

        # Check ownership
        if property_obj.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only edit your own properties.")

        # Owners can only edit DRAFT or REJECTED properties
        if not self.request.user.is_staff and property_obj.status not in ['draft', 'rejected']:
            raise PermissionDenied(
                f"You can only edit properties in DRAFT or REJECTED status. "
                f"Current status: {property_obj.status}. "
                f"Contact support if you need to modify an approved property."
            )

        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def submit_for_approval(self, request, pk=None):
        """
        Owner submits property for admin approval.

        POST /api/properties/{id}/submit-for-approval/
        """
        property_obj = self.get_object()

        # Check ownership
        if property_obj.owner != request.user:
            raise PermissionDenied("You can only submit your own properties for approval.")

        # Only DRAFT or REJECTED properties can be submitted
        if property_obj.status not in ['draft', 'rejected']:
            return Response(
                {'error': f'Only draft or rejected properties can be submitted. Current status: {property_obj.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate that property has at least one room type
        if not property_obj.room_types.exists():
            return Response(
                {
                    'error': 'Property must have at least one room type before submission',
                    'detail': 'Please add at least one room type to your property'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate required fields
        missing_fields = []
        if not property_obj.name:
            missing_fields.append('name')
        if not property_obj.description:
            missing_fields.append('description')
        if not property_obj.address:
            missing_fields.append('address')
        if not property_obj.city:
            missing_fields.append('city')
        if not property_obj.district:
            missing_fields.append('district')

        if missing_fields:
            return Response(
                {
                    'error': f'Missing required fields: {", ".join(missing_fields)}',
                    'detail': f'Please fill in all required fields before submission'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        property_obj.status = 'pending_approval'
        property_obj.submitted_at = now()
        property_obj.save()

        return Response(
            {
                'success': True,
                'message': 'Property submitted for approval',
                'data': PropertyDetailSerializer(property_obj).data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        """
        Approve a property (admin only).

        POST /api/properties/{id}/approve/
        """
        property_obj = self.get_object()

        # Only pending_approval properties can be approved
        if property_obj.status != 'pending_approval':
            return Response(
                {'error': f'Only pending properties can be approved. Current status: {property_obj.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        property_obj.status = 'approved'
        property_obj.reviewed_at = now()
        property_obj.reviewed_by = request.user
        property_obj.published_at = now()
        property_obj.save()

        return Response(
            {
                'success': True,
                'message': 'Property approved',
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
            "rejection_reason": "Description does not meet guidelines"
        }
        """
        property_obj = self.get_object()
        rejection_reason = request.data.get('rejection_reason', 'No reason provided')

        # Only pending_approval properties can be rejected
        if property_obj.status != 'pending_approval':
            return Response(
                {'error': f'Only pending properties can be rejected. Current status: {property_obj.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        property_obj.status = 'rejected'
        property_obj.rejection_reason = rejection_reason
        property_obj.reviewed_at = now()
        property_obj.reviewed_by = request.user
        property_obj.save()

        # TODO: Send email to owner with rejection reason

        return Response(
            {
                'success': True,
                'message': 'Property rejected',
                'rejection_reason': rejection_reason,
                'data': PropertyDetailSerializer(property_obj).data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def suspend(self, request, pk=None):
        """
        Suspend a property (admin only).

        POST /api/properties/{id}/suspend/
        """
        property_obj = self.get_object()

        if property_obj.status == 'suspended':
            return Response(
                {'error': 'Property is already suspended'},
                status=status.HTTP_400_BAD_REQUEST
            )

        property_obj.status = 'suspended'
        property_obj.save()

        # TODO: Send email to owner with suspension reason

        return Response(
            {
                'success': True,
                'message': 'Property suspended',
                'data': PropertyDetailSerializer(property_obj).data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def unsuspend(self, request, pk=None):
        """
        Unsuspend a property (admin only). Returns to APPROVED status.

        POST /api/properties/{id}/unsuspend/
        """
        property_obj = self.get_object()

        if property_obj.status != 'suspended':
            return Response(
                {'error': f'Only suspended properties can be unsuspended. Current status: {property_obj.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        property_obj.status = 'approved'
        property_obj.save()

        return Response(
            {
                'success': True,
                'message': 'Property unsuspended',
                'data': PropertyDetailSerializer(property_obj).data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def unpublish(self, request, pk=None):
        """
        Unpublish a property (admin only).

        POST /api/properties/{id}/unpublish/
        """
        property_obj = self.get_object()

        property_obj.status = 'unpublished'
        property_obj.save()

        return Response(
            {
                'success': True,
                'message': 'Property unpublished',
                'data': PropertyDetailSerializer(property_obj).data
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


class SearchViewSet(viewsets.ViewSet):
    """
    Advanced property search with filtering, sorting, and pagination.

    Query parameters:
    - city: Filter by city name
    - district: Filter by district
    - province: Filter by province
    - property_types: Comma-separated property type IDs
    - amenities: Comma-separated amenity IDs
    - min_price: Minimum room price
    - max_price: Maximum room price
    - min_rating: Minimum property rating
    - check_in: Check-in date (YYYY-MM-DD)
    - check_out: Check-out date (YYYY-MM-DD)
    - adults: Number of adults
    - children: Number of children
    - search: Text search (name, description, address)
    - sort_by: Sort field (newest, rating, price, name, reviews, popular)
    - sort_direction: asc or desc
    - page: Page number (default 1)
    - page_size: Items per page (default 20, max 100)
    """

    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'])
    def advanced(self, request):
        """
        Advanced search with all filters.

        GET /api/properties/search/advanced/?city=Colombo&min_price=1000&sort_by=rating
        """
        # Parse query parameters into filters
        filters = SearchFilters.from_query_params(request.query_params)

        # Create search service and apply filters
        search_service = PropertySearchService()
        search_service.build_query(filters)

        # Get pagination parameters
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)

        # Calculate offset
        offset = (page - 1) * page_size

        # Get total count
        total_count = search_service.count()

        # Get paginated results
        results = search_service.get_results(limit=page_size, offset=offset)

        # Serialize results
        serializer = PropertyCardSerializer(results, many=True)

        # Build pagination URLs (simplified)
        next_url = None
        previous_url = None

        if offset + page_size < total_count:
            next_url = request.build_absolute_uri(f"?page={page + 1}&page_size={page_size}")

        if page > 1:
            previous_url = request.build_absolute_uri(f"?page={page - 1}&page_size={page_size}")

        return Response(
            {
                'success': True,
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size,
                'next': next_url,
                'previous': previous_url,
                'results': serializer.data,
                'filters_applied': filters
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def by_destination(self, request):
        """
        Search properties by destination (city).

        GET /api/properties/search/by-destination/?city=Colombo
        """
        city = request.query_params.get('city')

        if not city:
            return Response(
                {'error': 'city parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        search_service = PropertySearchService()
        search_service.filter_by_destination(city=city)

        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        offset = (page - 1) * page_size

        total_count = search_service.count()
        results = search_service.get_results(limit=page_size, offset=offset)

        serializer = PropertyCardSerializer(results, many=True)

        return Response(
            {
                'success': True,
                'destination': city,
                'count': total_count,
                'results': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def by_price_range(self, request):
        """
        Search properties by price range.

        GET /api/properties/search/by-price-range/?min_price=1000&max_price=10000
        """
        try:
            min_price = request.query_params.get('min_price')
            max_price = request.query_params.get('max_price')

            if min_price:
                min_price = float(min_price)
            if max_price:
                max_price = float(max_price)

            search_service = PropertySearchService()
            search_service.filter_by_price_range(min_price=min_price, max_price=max_price)

            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 20)), 100)
            offset = (page - 1) * page_size

            total_count = search_service.count()
            results = search_service.get_results(limit=page_size, offset=offset)

            serializer = PropertyCardSerializer(results, many=True)

            return Response(
                {
                    'success': True,
                    'count': total_count,
                    'results': serializer.data
                },
                status=status.HTTP_200_OK
            )

        except ValueError as e:
            return Response(
                {'error': f'Invalid price range: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """
        Get featured/most popular properties.

        GET /api/properties/search/featured/?limit=10
        """
        limit = int(request.query_params.get('limit', 10))
        limit = min(limit, 50)

        search_service = PropertySearchService()
        search_service.sort_by('popular', 'desc')

        results = search_service.get_results(limit=limit)
        serializer = PropertyCardSerializer(results, many=True)

        return Response(
            {
                'success': True,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def newly_added(self, request):
        """
        Get newly added properties.

        GET /api/properties/search/newly-added/?limit=10
        """
        limit = int(request.query_params.get('limit', 10))
        limit = min(limit, 50)

        search_service = PropertySearchService()
        search_service.sort_by('newest', 'desc')

        results = search_service.get_results(limit=limit)
        serializer = PropertyCardSerializer(results, many=True)

        return Response(
            {
                'success': True,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """
        Get highest rated properties.

        GET /api/properties/search/top-rated/?limit=10
        """
        limit = int(request.query_params.get('limit', 10))
        limit = min(limit, 50)

        search_service = PropertySearchService()
        search_service.sort_by('rating', 'desc')

        results = search_service.get_results(limit=limit)
        serializer = PropertyCardSerializer(results, many=True)

        return Response(
            {
                'success': True,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )


class DestinationViewSetDetail(viewsets.ViewSet):
    """Destination detail view with properties"""

    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, slug=None):
        """
        Get destination details with properties.

        GET /api/properties/destinations/{slug}/
        """
        destination, properties = DestinationSearchService.get_properties_in_destination(slug)

        if not destination:
            return Response(
                {'error': 'Destination not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        destination_serializer = DestinationDetailSerializer(destination)

        return Response(
            {
                'success': True,
                'data': destination_serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """
        Get popular destinations.

        GET /api/properties/destinations/popular/
        """
        limit = int(request.query_params.get('limit', 10))
        limit = min(limit, 50)

        destinations = DestinationSearchService.get_popular_destinations(limit)
        serializer = DestinationSerializer(destinations, many=True)

        return Response(
            {
                'success': True,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def by_region(self, request):
        """
        Get destinations by region.

        GET /api/properties/destinations/by-region/?province=Southern
        """
        province = request.query_params.get('province')
        district = request.query_params.get('district')

        destinations = DestinationSearchService.get_destinations_by_region(
            province=province,
            district=district
        )

        serializer = DestinationSerializer(destinations, many=True)

        return Response(
            {
                'success': True,
                'data': serializer.data
            },
            status=status.HTTP_200_OK
        )
