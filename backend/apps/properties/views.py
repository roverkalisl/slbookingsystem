"""
Views for property management.
"""

import logging
import time
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
import cloudinary.utils

logger = logging.getLogger(__name__)

# Room photo rule: each room needs 1-5 photos (minimum checked at submission,
# maximum enforced on upload). Property photos have their own rules below.
ROOM_PHOTOS_MIN = 1
ROOM_PHOTOS_MAX = 5

# Whole-property listings (PropertyType.booking_mode == 'whole_property', e.g.
# Entry Villa) are booked through one system-managed RoomType with this name.
VILLA_UNIT_NAME = 'Entire Villa'
ROOMS_NOT_APPLICABLE = (
    'Rooms are not applicable for Entry Villa - the villa is booked as a whole. '
    'Set the Villa Details (capacity, beds and price) instead.'
)
VILLA_UNIT_MANAGED = (
    'The "Entire Villa" unit is managed automatically - edit it through the Villa Details instead.'
)


def villa_details_payload(unit):
    """Villa-level details (from the system-managed unit) for the API."""
    if unit is None:
        return {'configured': False, 'unit_id': None}
    pricing = getattr(unit, 'pricing', None)
    return {
        'configured': True,
        'unit_id': str(unit.id),
        'max_adults': unit.max_adults,
        'max_children': unit.max_children,
        'total_occupancy': unit.total_occupancy,
        'number_of_beds': unit.number_of_beds,
        'bed_configuration': unit.bed_configuration,
        'bathroom_type': unit.bathroom_type,
        'base_price': str(pricing.base_price) if pricing else None,
        'weekend_price': str(pricing.weekend_price) if pricing and pricing.weekend_price else None,
    }

from .models import (
    PropertyType, Amenity, Destination, Property, PropertyPhoto,
    RoomType, RoomTypePhoto, Pricing, SeasonalRate
)
from .serializers import (
    PropertyTypeSerializer, AmenitySerializer, DestinationSerializer,
    PropertyListSerializer, PropertyDetailSerializer,
    PropertyCreateUpdateSerializer, PropertyApprovalSerializer,
    RoomTypeListSerializer, RoomTypeDetailSerializer, RoomTypeCreateSerializer,
    PropertyPhotoSerializer, RoomTypePhotoSerializer,
    PricingSerializer, PricingUpdateSerializer, SeasonalRateSerializer,
    VillaDetailsSerializer, bookable_room_types_of, cover_url_of,
    PropertyCardSerializer, SearchFilterSerializer,
    DestinationDetailSerializer, SearchResultsSerializer
)
from .pricing import PricingCalculator
from .search import PropertySearchService, DestinationSearchService, SearchFilters


def build_cloudinary_signature(folder: str) -> dict:
    """
    Build a signed-upload payload for direct browser-to-Cloudinary uploads.

    Used instead of an unsigned upload preset (which would need to be
    created by hand in the Cloudinary dashboard - not something this code
    can provision). Signing server-side with the existing API secret lets
    the frontend upload directly to Cloudinary without ever seeing that
    secret, while still tying the upload to a specific property/room folder.
    """
    api_key = settings.CLOUDINARY_STORAGE.get('API_KEY')
    api_secret = settings.CLOUDINARY_STORAGE.get('API_SECRET')
    cloud_name = settings.CLOUDINARY_STORAGE.get('CLOUD_NAME')

    if not (api_key and api_secret and cloud_name):
        return None

    timestamp = int(time.time())
    params_to_sign = {'timestamp': timestamp, 'folder': folder}
    signature = cloudinary.utils.api_sign_request(params_to_sign, api_secret)

    return {
        'signature': signature,
        'timestamp': timestamp,
        'api_key': api_key,
        'cloud_name': cloud_name,
        'folder': folder,
    }


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
        logger.debug(f"[VIEWSET] get_queryset called for user={user.id if user.is_authenticated else 'anonymous'}")

        # Unauthenticated users see approved properties only
        if not user.is_authenticated:
            logger.debug(f"[VIEWSET] User unauthenticated, returning approved properties only")
            return Property.objects.filter(status='approved')

        # Guests see approved properties only
        if user.has_role('guest'):
            logger.debug(f"[VIEWSET] User is guest, returning approved properties only")
            return Property.objects.filter(status='approved')

        # Property owners see:
        # - Their own properties (all statuses)
        # - Other owners' approved properties
        if user.has_role('property_owner'):
            queryset = Property.objects.filter(
                owner=user
            ) | Property.objects.filter(status='approved')
            logger.debug(f"[VIEWSET] User is property_owner, queryset count={queryset.count()}")
            return queryset

        # Super admin sees everything
        if user.is_staff:
            logger.debug(f"[VIEWSET] User is staff, returning all properties")
            return Property.objects.all()

        # Default: show only approved properties
        logger.debug(f"[VIEWSET] Default: returning approved properties only")
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
        logger.info(f"[VIEWSET] perform_update called for pk={self.kwargs.get('pk')}")
        logger.info(f"[VIEWSET] user={self.request.user.id if hasattr(self.request, 'user') else 'unknown'}")

        property_obj = self.get_object()
        logger.info(f"[VIEWSET] get_object() returned property={property_obj.id}, owner={property_obj.owner.id}, status={property_obj.status}")

        # Check ownership
        if property_obj.owner != self.request.user and not self.request.user.is_staff:
            logger.warning(f"[VIEWSET] Permission denied: owner mismatch")
            raise PermissionDenied("You can only edit your own properties.")

        # Owners can only edit DRAFT or REJECTED properties
        if not self.request.user.is_staff and property_obj.status not in ['draft', 'rejected']:
            logger.warning(f"[VIEWSET] Permission denied: status not draft/rejected")
            raise PermissionDenied(
                f"You can only edit properties in DRAFT or REJECTED status. "
                f"Current status: {property_obj.status}. "
                f"Contact support if you need to modify an approved property."
            )

        logger.info(f"[VIEWSET] Update permitted, saving")
        serializer.save()

    def perform_destroy(self, instance):
        """Delete property (only its owner or an admin)"""
        # Approved properties are in every authenticated user's queryset, so
        # ownership must be checked explicitly here.
        if instance.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only delete your own properties.")
        instance.delete()

    # Photos required before a property can be submitted for approval.
    # Property photos: minimum 5, no product maximum (see MAX_PROPERTY_PHOTOS).
    # Room photos: 1-5 per room (ROOM_PHOTOS_MIN / ROOM_PHOTOS_MAX).
    MIN_PROPERTY_PHOTOS = 5
    MIN_ROOM_PHOTOS = ROOM_PHOTOS_MIN

    def _submission_errors(self, property_obj: Property) -> list:
        """
        Return every reason this property cannot yet be submitted for approval
        (empty list when it is ready). Drafts may stay incomplete - these rules
        apply only at submission.

        Availability uses the existing architecture: rooms are bookable by
        default and inventory comes from RoomType.total_rooms (Availability
        rows only record owner blocks and booked dates), so a room has
        availability configured when it offers at least 1 room.
        """
        errors = []

        required_fields = ['name', 'description', 'address', 'city', 'district']
        missing_fields = [field for field in required_fields if not getattr(property_obj, field)]
        if missing_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}.")

        photo_count = property_obj.photos.count()
        if photo_count < self.MIN_PROPERTY_PHOTOS:
            errors.append(
                f"Property must have at least {self.MIN_PROPERTY_PHOTOS} photos (currently {photo_count})."
            )

        # Entry Villa (whole property): the villa itself is the unit - no
        # owner-created rooms and no room photos; its property photos are the gallery.
        if property_obj.is_whole_property:
            return errors + self._villa_submission_errors(property_obj)

        # Only active rooms are submitted for booking; deactivated rooms are skipped.
        rooms = list(
            property_obj.room_types.filter(is_active=True)
            .select_related('pricing')
            .prefetch_related('photos')
        )
        if not rooms:
            errors.append("Property must have at least one active room type.")

        for room in rooms:
            # Minimum only: rooms that already have more than ROOM_PHOTOS_MAX
            # (uploaded before the cap existed) are still valid - existing
            # photos are never deleted automatically.
            if len(room.photos.all()) < self.MIN_ROOM_PHOTOS:
                errors.append(f"Room '{room.name}' must have at least 1 photo.")

            pricing = getattr(room, 'pricing', None)
            if pricing is None or not pricing.base_price or pricing.base_price <= 0:
                errors.append(f"Room '{room.name}' does not have pricing configured.")

            if room.total_rooms < 1:
                errors.append(
                    f"Availability has not been configured for room '{room.name}' "
                    f"(number of rooms must be at least 1)."
                )

        return errors

    @staticmethod
    def _villa_submission_errors(property_obj: Property) -> list:
        """Submission rules for a whole-property listing (Entry Villa)."""
        errors = []
        unit = property_obj.room_types.filter(is_property_unit=True).select_related('pricing').first()
        if unit is None:
            errors.append('Villa details have not been set (capacity, beds and nightly price).')
        else:
            if unit.max_adults < 1 or unit.total_occupancy < 1:
                errors.append('Villa capacity has not been configured.')
            pricing = getattr(unit, 'pricing', None)
            if pricing is None or not pricing.base_price or pricing.base_price <= 0:
                errors.append('Villa pricing has not been configured.')
            if not unit.is_active or unit.total_rooms != 1:
                errors.append('Villa availability has not been configured.')

        legacy_rooms = list(
            property_obj.room_types.filter(is_active=True, is_property_unit=False).values_list('name', flat=True)
        )
        if legacy_rooms:
            errors.append(
                'An Entry Villa is booked as a whole and cannot have separate rooms '
                f"({', '.join(legacy_rooms)}). Save the Villa Details to replace them."
            )
        return errors

    @action(detail=True, methods=['get', 'put'], permission_classes=[permissions.IsAuthenticatedOrReadOnly], url_path='villa')
    def villa(self, request, pk=None):
        """
        Villa-level details of a whole-property listing (Entry Villa).

        GET /api/properties/{id}/villa/
        PUT /api/properties/{id}/villa/
        {
            "max_adults": 4, "max_children": 2, "total_occupancy": 6,
            "number_of_beds": 3, "bed_configuration": "king", "bathroom_type": "private",
            "base_price": "25000.00", "weekend_price": "30000.00"
        }

        Stored on the system-managed "Entire Villa" RoomType
        (is_property_unit=True, total_rooms=1) and its Pricing, so booking,
        availability, search, notifications and payments keep using the
        existing room-type architecture. The first save deactivates - never
        deletes - any legacy owner-created rooms of the villa.
        """
        property_obj = self.get_object()
        if not property_obj.is_whole_property:
            return Response(
                {'error': 'Villa details only apply to whole-property listings such as Entry Villa. '
                          'Manage rooms for this property instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'GET':
            unit = property_obj.unit
            return Response({'success': True, 'data': villa_details_payload(unit)}, status=status.HTTP_200_OK)

        # Same editing rules as the property itself
        if property_obj.owner != request.user and not request.user.is_staff:
            raise PermissionDenied('You can only edit your own properties.')
        if not request.user.is_staff and property_obj.status not in ['draft', 'rejected']:
            raise PermissionDenied(
                f'You can only edit properties in DRAFT or REJECTED status. Current status: {property_obj.status}.'
            )

        serializer = VillaDetailsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data

        with transaction.atomic():
            unit = property_obj.room_types.select_for_update().filter(is_property_unit=True).first()
            if unit is None:
                unit = RoomType(property=property_obj, is_property_unit=True, name=VILLA_UNIT_NAME,
                                room_type='villa')
            unit.name = VILLA_UNIT_NAME
            unit.is_active = True
            unit.total_rooms = 1  # the villa is a single bookable unit
            for field in ('max_adults', 'max_children', 'total_occupancy',
                          'number_of_beds', 'bed_configuration', 'bathroom_type'):
                setattr(unit, field, values[field])
            unit.save()

            pricing = Pricing.objects.filter(room_type=unit).first() or Pricing(room_type=unit)
            pricing.base_price = values['base_price']
            if 'weekend_price' in values:
                pricing.weekend_price = values['weekend_price']
            pricing.save()

            # Legacy owner-created rooms of this villa stop being bookable.
            # Deactivated, never deleted - bookings reference them (CASCADE).
            property_obj.room_types.filter(is_property_unit=False, is_active=True).update(is_active=False)

        unit.refresh_from_db()
        return Response({'success': True, 'data': villa_details_payload(unit)}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='submit-for-approval')
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

        errors = self._submission_errors(property_obj)
        if errors:
            return Response(
                {
                    'error': 'Property is not ready for approval. ' + ' '.join(errors),
                    'detail': errors[0],
                    'errors': errors,
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

        try:
            from apps.notifications.models import Notification
            from apps.notifications.service import EmailChannel
            subject = f'Your property "{property_obj.name}" has been approved'
            message = f'Good news - "{property_obj.name}" is now live and visible to guests on SL Booking.'
            result = EmailChannel().send(recipient=property_obj.owner.email, subject=subject, message=message)
            Notification.objects.create(
                recipient=property_obj.owner, notification_type='property_approved',
                title=subject, message=message, channel='email',
                status='sent' if result['success'] else 'failed'
            )
        except Exception:
            logger.exception('Failed to send property-approved notification for property %s', property_obj.id)

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

        try:
            from apps.notifications.models import Notification
            from apps.notifications.service import EmailChannel
            subject = f'Your property "{property_obj.name}" was not approved'
            message = f'"{property_obj.name}" could not be approved. Reason: {rejection_reason}\n\nYou can edit and resubmit it for review.'
            result = EmailChannel().send(recipient=property_obj.owner.email, subject=subject, message=message)
            Notification.objects.create(
                recipient=property_obj.owner, notification_type='property_rejected',
                title=subject, message=message, channel='email',
                status='sent' if result['success'] else 'failed'
            )
        except Exception:
            logger.exception('Failed to send property-rejected notification for property %s', property_obj.id)

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

    # Practical upload ceiling to protect storage/DB from abuse - NOT a product
    # limit. Owners can upload as many photos as they need well below this.
    MAX_PROPERTY_PHOTOS = 50

    @action(detail=True, methods=['get'], url_path='upload-signature')
    def upload_signature(self, request, pk=None):
        """
        GET /api/properties/{id}/upload-signature/

        Returns signed params so the browser can upload a property photo
        directly to Cloudinary, then POST the resulting URL to add_photo().
        """
        property_obj = self.get_object()
        if property_obj.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You can only upload photos to your own properties.")

        payload = build_cloudinary_signature(f'slbooking/properties/{property_obj.id}')
        if payload is None:
            return Response({'error': 'Image uploads are not configured on this server.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({'success': True, 'data': payload}, status=status.HTTP_200_OK)

    @photos.mapping.post
    def add_photo(self, request, pk=None):
        """Add one owner-managed property photo. No fixed product maximum -
        see MAX_PROPERTY_PHOTOS for the abuse-prevention ceiling only."""
        property_obj = self.get_object()
        if property_obj.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You can only add photos to your own properties.")
        if property_obj.photos.count() >= self.MAX_PROPERTY_PHOTOS:
            return Response(
                {'error': f'A property can have at most {self.MAX_PROPERTY_PHOTOS} photos.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cloudinary_url = request.data.get('cloudinary_url')
        cloudinary_public_id = request.data.get('cloudinary_public_id')
        if not cloudinary_url or not cloudinary_public_id:
            return Response({'error': 'cloudinary_url and cloudinary_public_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            photo = PropertyPhoto.objects.create(
                property=property_obj,
                cloudinary_url=cloudinary_url,
                cloudinary_public_id=cloudinary_public_id,
                display_order=property_obj.photos.count(),
            )
            # The first photo of a property becomes its cover automatically.
            property_obj.ensure_cover_photo()
            photo.refresh_from_db()
        return Response({'success': True, 'data': PropertyPhotoSerializer(photo).data}, status=status.HTTP_201_CREATED)

    @staticmethod
    def _photo_state(property_obj):
        """Cover URL + ordered photo list, returned after every cover change."""
        return {
            'cover_photo_url': cover_url_of(property_obj),
            'photos': PropertyPhotoSerializer(property_obj.photos.order_by('display_order', 'created_at'), many=True).data,
        }

    @staticmethod
    def _find_property_photo(property_obj, photo_id):
        """The photo with this id ON THIS property, or None (also for malformed ids)."""
        try:
            return PropertyPhoto.objects.filter(id=photo_id, property=property_obj).first()
        except (ValueError, DjangoValidationError):
            return None

    @action(detail=True, methods=['delete'], url_path='delete-photo')
    def delete_photo(self, request, photo_id=None, pk=None):
        """
        Delete a property photo. Deleting the cover promotes the first
        remaining photo; deleting the last photo clears the cover.

        DELETE /api/properties/{property_id}/delete-photo/?photo_id=<photo_id>
        """
        property_obj = self.get_object()
        if property_obj.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You can only delete photos from your own properties.")

        photo_id = request.query_params.get('photo_id') or self.kwargs.get('photo_id')
        if not photo_id:
            return Response({'error': 'photo_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        photo = self._find_property_photo(property_obj, photo_id)
        if photo is None:
            return Response({'error': 'Photo not found'}, status=status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            photo.delete()
            property_obj.ensure_cover_photo()
        return Response(
            {'success': True, 'message': 'Photo deleted successfully', 'data': self._photo_state(property_obj)},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='set-cover')
    def set_cover(self, request, pk=None):
        """
        Make one of the property's existing photos its cover (no re-upload).
        The previous cover becomes a normal photo.

        POST /api/properties/{property_id}/set-cover/   {"photo_id": "<photo uuid>"}
        """
        property_obj = self.get_object()
        if property_obj.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You can only change the cover photo of your own properties.")

        photo_id = request.data.get('photo_id')
        if not photo_id:
            return Response({'error': 'photo_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Scoped to this property: another property's photo is simply "not found".
        photo = self._find_property_photo(property_obj, photo_id)
        if photo is None:
            return Response({'error': 'Photo not found for this property'}, status=status.HTTP_404_NOT_FOUND)

        property_obj.set_cover_photo(photo)
        return Response(
            {'success': True, 'message': 'Cover photo updated', 'data': self._photo_state(property_obj)},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['get', 'post'])
    def rooms(self, request, pk=None):
        """
        Get all room types for a property.

        GET /api/properties/{id}/rooms/
        """
        property_obj = self.get_object()
        if request.method == 'POST':
            if property_obj.owner != request.user and not request.user.is_staff:
                raise PermissionDenied("You can only add rooms to your own properties.")
            if property_obj.is_whole_property:
                return Response({'error': ROOMS_NOT_APPLICABLE}, status=status.HTTP_400_BAD_REQUEST)
            serializer = RoomTypeCreateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            room = RoomType.objects.create(property=property_obj, **serializer.validated_data)
            return Response({'success': True, 'data': RoomTypeDetailSerializer(room).data}, status=status.HTTP_201_CREATED)

        # Whole-property listings expose only their "Entire Villa" unit (used
        # by the owner calendar); room-based properties list every room type.
        rooms = bookable_room_types_of(property_obj)
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
                property__status='approved',
                is_active=True
            )

        if user.has_role('property_owner'):
            return RoomType.objects.filter(
                property__owner=user
            ) | RoomType.objects.filter(property__status='approved')

        if user.is_staff:
            return RoomType.objects.all()

        return RoomType.objects.filter(
            property__status='approved',
            is_active=True
        )

    def perform_create(self, serializer):
        """Create room type"""
        property_obj = serializer.validated_data['property']

        # Check ownership
        if property_obj.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only add rooms to your own properties.")
        if property_obj.is_whole_property:
            raise ValidationError({'error': ROOMS_NOT_APPLICABLE})

        serializer.save()

    def perform_update(self, serializer):
        """Update room type"""
        room_type = self.get_object()

        # Check ownership
        if room_type.property.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only edit rooms in your own properties.")
        if room_type.is_property_unit:
            raise ValidationError({'error': VILLA_UNIT_MANAGED})

        serializer.save()

    def perform_destroy(self, instance):
        """Delete room type (only the property's owner or an admin)"""
        # Rooms of approved properties are in every authenticated user's
        # queryset, so ownership must be checked explicitly here.
        if instance.property.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You can only delete rooms in your own properties.")
        if instance.is_property_unit:
            raise ValidationError({'error': VILLA_UNIT_MANAGED})
        instance.delete()

    @action(detail=True, methods=['get'], url_path='upload-signature', permission_classes=[permissions.IsAuthenticated])
    def upload_signature(self, request, pk=None):
        """
        GET /api/properties/rooms/{id}/upload-signature/

        Returns signed params so the browser can upload a room photo
        directly to Cloudinary, then POST the resulting URL to add_photo().
        """
        room_type = self.get_object()
        if room_type.property.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You can only upload photos to your own rooms.")

        payload = build_cloudinary_signature(f'slbooking/rooms/{room_type.id}')
        if payload is None:
            return Response({'error': 'Image uploads are not configured on this server.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({'success': True, 'data': payload}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='add-photo')
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

        Each room can have 1-5 photos: at most ROOM_PHOTOS_MAX, enforced here
        server-side (a 6th photo is rejected with 400).
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

        with transaction.atomic():
            # Lock the room so two concurrent uploads can't both pass the cap.
            RoomType.objects.select_for_update().get(pk=room_type.pk)
            if room_type.photos.count() >= ROOM_PHOTOS_MAX:
                return Response(
                    {'error': f'A room can have at most {ROOM_PHOTOS_MAX} photos. '
                              f'Delete a photo before uploading another.'},
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

    @action(detail=True, methods=['delete'], url_path='delete-photo')
    def delete_photo(self, request, pk=None):
        """
        Delete a room type photo.

        DELETE /api/properties/rooms/{room_id}/delete-photo/?photo_id=<photo_id>
        """
        room_type = self.get_object()
        if room_type.property.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You can only delete photos from your own rooms.")

        photo_id = request.query_params.get('photo_id')
        if not photo_id:
            return Response({'error': 'photo_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            photo = RoomTypePhoto.objects.get(id=photo_id, room_type=room_type)
            photo.delete()
            return Response({'success': True, 'message': 'Photo deleted successfully'}, status=status.HTTP_200_OK)
        except RoomTypePhoto.DoesNotExist:
            return Response({'error': 'Photo not found'}, status=status.HTTP_404_NOT_FOUND)

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

            # Validate owner input (positive prices only; platform fee/tax are
            # never accepted from the client).
            input_serializer = PricingUpdateSerializer(data=request.data)
            input_serializer.is_valid(raise_exception=True)
            values = input_serializer.validated_data

            pricing = Pricing.objects.filter(room_type=room_type).first()
            if pricing is None:
                # base_price is a required column - creating pricing without it
                # previously raised an IntegrityError (500).
                if values.get('base_price') is None:
                    return Response(
                        {'error': 'base_price is required.', 'base_price': ['This field is required.']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                pricing = Pricing(room_type=room_type, base_price=values['base_price'])

            # Update only the fields that were sent
            for field in ('base_price', 'weekend_price', 'extra_guest_fee', 'child_fee'):
                if field in values:
                    setattr(pricing, field, values[field])

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

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated], url_path='calendar')
    def owner_calendar(self, request, pk=None):
        """
        Owner-facing per-date availability for this room type.

        GET /api/properties/rooms/{id}/calendar/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
        Defaults to the current calendar month when no range is given.

        Reuses the existing Booking/Availability models - no new
        availability model or calendar-specific storage is introduced.
        """
        import calendar as calendar_module
        from datetime import date as date_cls, timedelta
        from apps.bookings.models import Booking, Availability

        room_type = self.get_object()
        if room_type.property.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You can only view the calendar for your own rooms.")

        start_param = request.query_params.get('start_date')
        end_param = request.query_params.get('end_date')
        if start_param and end_param:
            start_date = date_cls.fromisoformat(start_param)
            end_date = date_cls.fromisoformat(end_param)
        else:
            today = date_cls.today()
            start_date = today.replace(day=1)
            last_day = calendar_module.monthrange(today.year, today.month)[1]
            end_date = today.replace(day=last_day)

        bookings = Booking.objects.filter(
            room_type=room_type,
            status__in=['pending', 'confirmed', 'payment_pending', 'paid', 'completed'],
            check_in_date__lte=end_date,
            check_out_date__gt=start_date,
        ).values('check_in_date', 'check_out_date', 'booking_reference', 'status', 'number_of_rooms')

        blocked_dates = set(
            Availability.objects.filter(
                room_type=room_type, date__gte=start_date, date__lte=end_date, status__in=['blocked', 'maintenance']
            ).values_list('date', flat=True)
        )

        days = []
        current = start_date
        while current <= end_date:
            # Sum rooms held, not booking rows - one booking may hold several rooms.
            booked_count = sum(b['number_of_rooms'] for b in bookings if b['check_in_date'] <= current < b['check_out_date'])
            is_blocked = current in blocked_dates
            days.append({
                'date': current.isoformat(),
                'total_rooms': room_type.total_rooms,
                'booked_count': booked_count,
                'available_count': 0 if is_blocked else max(room_type.total_rooms - booked_count, 0),
                'is_blocked': is_blocked,
            })
            current += timedelta(days=1)

        return Response({'success': True, 'data': {'room_type_id': str(room_type.id), 'days': days}}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='block-dates')
    def block_dates(self, request, pk=None):
        """
        Block a date range for this room type (e.g. maintenance, owner use).

        POST /api/properties/rooms/{id}/block-dates/
        { "start_date": "2026-10-01", "end_date": "2026-10-03" }
        """
        from datetime import date as date_cls, timedelta
        from apps.bookings.models import Availability

        room_type = self.get_object()
        if room_type.property.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You can only block dates for your own rooms.")

        try:
            start_date = date_cls.fromisoformat(request.data.get('start_date', ''))
            end_date = date_cls.fromisoformat(request.data.get('end_date', ''))
        except ValueError:
            return Response({'error': 'start_date and end_date must be valid ISO dates (YYYY-MM-DD).'}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response({'error': 'start_date must not be after end_date.'}, status=status.HTTP_400_BAD_REQUEST)

        current = start_date
        while current <= end_date:
            Availability.objects.update_or_create(
                room_type=room_type, date=current,
                defaults={'status': 'blocked', 'available_count': 0}
            )
            current += timedelta(days=1)

        return Response({'success': True, 'message': 'Dates blocked successfully'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='unblock-dates')
    def unblock_dates(self, request, pk=None):
        """
        Release a previously blocked date range back to available.

        POST /api/properties/rooms/{id}/unblock-dates/
        { "start_date": "2026-10-01", "end_date": "2026-10-03" }
        """
        from datetime import date as date_cls
        from apps.bookings.models import Availability

        room_type = self.get_object()
        if room_type.property.owner != request.user and not request.user.is_staff:
            raise PermissionDenied("You can only unblock dates for your own rooms.")

        try:
            start_date = date_cls.fromisoformat(request.data.get('start_date', ''))
            end_date = date_cls.fromisoformat(request.data.get('end_date', ''))
        except ValueError:
            return Response({'error': 'start_date and end_date must be valid ISO dates (YYYY-MM-DD).'}, status=status.HTTP_400_BAD_REQUEST)

        Availability.objects.filter(
            room_type=room_type, date__gte=start_date, date__lte=end_date, status__in=['blocked', 'maintenance']
        ).update(status='available', available_count=room_type.total_rooms)

        return Response({'success': True, 'message': 'Dates unblocked successfully'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def calculate_price(self, request, pk=None):
        """
        Calculate price for a booking.

        GET /api/properties/rooms/{id}/calculate-price/?check_in=2026-09-15&check_out=2026-09-17&adults=2&children=0&rooms=1

        Query Parameters:
        - check_in: Check-in date (YYYY-MM-DD)
        - check_out: Check-out date (YYYY-MM-DD)
        - adults: Number of adults
        - children: Number of children
        - rooms: Number of rooms (optional, default 1)

        Client-supplied discounts are not accepted - the quote matches what a
        booking would store.
        """
        room_type = self.get_object()

        try:
            check_in_str = request.query_params.get('check_in')
            check_out_str = request.query_params.get('check_out')
            adults = int(request.query_params.get('adults', 1))
            children = int(request.query_params.get('children', 0))
            rooms = int(request.query_params.get('rooms', 1))

            from datetime import datetime
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()

            # Calculate price
            calculator = PricingCalculator(room_type)
            price_breakdown = calculator.calculate_booking_price(
                check_in, check_out,
                num_adults=adults,
                num_children=children,
                num_rooms=rooms,
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
