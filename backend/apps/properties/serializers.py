"""
Serializers for property management.
"""

from decimal import Decimal

from rest_framework import serializers
from django.db import models
from .models import (
    PropertyType, Amenity, Destination, Property, PropertyPhoto,
    PropertyAmenity, RoomType, RoomTypePhoto, RoomTypeAmenity,
    Pricing, SeasonalRate, PropertyContact
)


class PropertyTypeSerializer(serializers.ModelSerializer):
    """Serializer for property types"""
    class Meta:
        model = PropertyType
        fields = ['id', 'name', 'description', 'is_active', 'booking_mode']
        read_only_fields = ['id', 'booking_mode']


def booking_mode_of(property_obj) -> str:
    """'whole_property' (e.g. Entry Villa) or 'room_types' (hotels, resorts...)."""
    return (
        PropertyType.BOOKING_MODE_WHOLE_PROPERTY if property_obj.is_whole_property
        else PropertyType.BOOKING_MODE_ROOM_TYPES
    )


def bookable_room_types_of(property_obj):
    """
    Room types that represent this property's bookable inventory.
    Whole-property listings expose ONLY their system-managed unit (legacy
    owner-created rooms are hidden); room-based properties are unchanged.
    """
    if property_obj.is_whole_property:
        return property_obj.room_types.filter(is_property_unit=True)
    return property_obj.room_types.all()


def starting_price_of(property_obj):
    """Lowest base price across the bookable room types (the villa's own price for Entry Villa)."""
    min_price = bookable_room_types_of(property_obj).aggregate(min=models.Min('pricing__base_price'))['min']
    return str(min_price) if min_price else None


def cover_url_of(property_obj):
    """
    Cloudinary URL of the property's cover photo (the PropertyPhoto flagged
    is_cover), falling back to the first photo by display order. None when
    the property has no photos. Reads photos.all() so a prefetch is reused.
    """
    photos = sorted(property_obj.photos.all(), key=lambda p: (not p.is_cover, p.display_order, p.created_at))
    return photos[0].cloudinary_url if photos else None


class AmenitySerializer(serializers.ModelSerializer):
    """Serializer for amenities"""
    class Meta:
        model = Amenity
        fields = ['id', 'name', 'slug', 'icon_url', 'category', 'is_active']
        read_only_fields = ['id', 'slug']


class DestinationSerializer(serializers.ModelSerializer):
    """Serializer for destinations"""
    class Meta:
        model = Destination
        fields = [
            'id', 'name', 'slug', 'description', 'cover_image_url',
            'city', 'district', 'province',
            'seo_title', 'seo_description', 'seo_keywords',
            'is_published', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']


class PropertyContactSerializer(serializers.ModelSerializer):
    """Serializer for property contact information"""
    class Meta:
        model = PropertyContact
        fields = [
            'id', 'contact_person_name', 'contact_phone', 'whatsapp_number',
            'email', 'emergency_contact', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PropertyPhotoSerializer(serializers.ModelSerializer):
    """Serializer for property photos"""
    class Meta:
        model = PropertyPhoto
        fields = [
            'id', 'cloudinary_url', 'cloudinary_public_id', 'caption',
            'display_order', 'is_cover', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PropertyAmenitySerializer(serializers.Serializer):
    """Serializer for property amenities (read/write)"""
    id = serializers.IntegerField(write_only=True)
    name = serializers.CharField(source='amenity.name', read_only=True)
    slug = serializers.CharField(source='amenity.slug', read_only=True)
    icon_url = serializers.URLField(source='amenity.icon_url', read_only=True)
    category = serializers.CharField(source='amenity.category', read_only=True)


class RoomTypePhotoSerializer(serializers.ModelSerializer):
    """Serializer for room type photos"""
    class Meta:
        model = RoomTypePhoto
        fields = [
            'id', 'cloudinary_url', 'cloudinary_public_id',
            'display_order', 'is_cover', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class RoomTypeAmenitySerializer(serializers.Serializer):
    """Serializer for room type amenities"""
    id = serializers.IntegerField(write_only=True)
    name = serializers.CharField(source='amenity.name', read_only=True)
    slug = serializers.CharField(source='amenity.slug', read_only=True)
    category = serializers.CharField(source='amenity.category', read_only=True)


class RoomTypeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating room types (accepts room data from frontend)"""
    amenity_ids = serializers.PrimaryKeyRelatedField(
        queryset=Amenity.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='amenities'
    )

    class Meta:
        model = RoomType
        fields = [
            'name', 'description', 'room_type', 'max_adults', 'max_children', 'total_occupancy',
            'bed_configuration', 'bathroom_type', 'number_of_beds', 'total_rooms',
            'room_size_sqft', 'view_type', 'amenity_ids'
        ]
        extra_kwargs = {
            'max_adults': {'min_value': 1},
            'max_children': {'min_value': 0},
            'total_occupancy': {'required': False, 'min_value': 1},
            'total_rooms': {'min_value': 1},
            'number_of_beds': {'min_value': 1},
        }

    def validate(self, attrs):
        # The add-room form collects max adults/children but not a separate
        # occupancy. Without this, total_occupancy silently stayed at the
        # model default of 2 - so a 4-adult room could only ever take 2 guests.
        if attrs.get('total_occupancy') is None:
            attrs['total_occupancy'] = attrs.get('max_adults', 2) + attrs.get('max_children', 0)
        return attrs


class RoomTypeListSerializer(serializers.ModelSerializer):
    """Serializer for room type list view"""
    amenities = serializers.SerializerMethodField()
    photos = RoomTypePhotoSerializer(many=True, read_only=True)
    pricing = serializers.SerializerMethodField()

    class Meta:
        model = RoomType
        fields = [
            'id', 'name', 'slug', 'description', 'room_type', 'max_adults', 'max_children',
            'total_occupancy', 'bed_configuration', 'bathroom_type', 'number_of_beds', 'total_rooms',
            'room_size_sqft', 'view_type', 'is_active', 'is_property_unit', 'amenities', 'photos', 'pricing', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'is_property_unit', 'created_at']

    def get_amenities(self, obj):
        amenities = obj.roomtypeamenity_set.all()
        return RoomTypeAmenitySerializer(amenities, many=True).data

    def get_pricing(self, obj):
        # OneToOneField - accessing obj.pricing directly raises
        # RelatedObjectDoesNotExist when a room type has no pricing row yet
        # (e.g. a brand-new room the owner hasn't priced). Guard with getattr.
        pricing = getattr(obj, 'pricing', None)
        if pricing is None:
            return None
        return PricingSerializer(pricing).data


class RoomTypeDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for room type with all information"""
    amenities = serializers.SerializerMethodField()
    photos = RoomTypePhotoSerializer(many=True, read_only=True)

    class Meta:
        model = RoomType
        fields = [
            'id', 'property', 'name', 'slug', 'description', 'room_type',
            'max_adults', 'max_children', 'total_occupancy',
            'bed_configuration', 'bathroom_type', 'number_of_beds', 'total_rooms', 'room_size_sqft',
            'view_type', 'is_active', 'is_property_unit', 'amenities', 'photos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'is_property_unit', 'created_at', 'updated_at']

    def get_amenities(self, obj):
        amenities = obj.roomtypeamenity_set.all()
        return RoomTypeAmenitySerializer(amenities, many=True).data


class PropertyListSerializer(serializers.ModelSerializer):
    """Serializer for property list view"""
    property_type_name = serializers.CharField(source='property_type.name', read_only=True)
    booking_mode = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()
    owner_info = serializers.SerializerMethodField()
    cover_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'name', 'slug', 'short_description', 'city', 'district',
            'status', 'submitted_at', 'rejection_reason', 'house_rules',
            'cover_photo_url', 'property_type_name', 'booking_mode', 'average_rating',
            'total_reviews', 'amenities', 'photo_count', 'owner_info', 'created_at', 'published_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'published_at', 'submitted_at']

    def get_booking_mode(self, obj):
        return booking_mode_of(obj)

    def get_cover_photo_url(self, obj):
        return cover_url_of(obj)

    def get_amenities(self, obj):
        amenities = obj.propertyamenity_set.all()[:5]  # Show first 5
        return [{'name': pa.amenity.name, 'slug': pa.amenity.slug} for pa in amenities]

    def get_owner_info(self, obj):
        """Owner contact for the admin review queue - staff only (this list is
        also public for approved properties, so never expose it to others)."""
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated or not request.user.is_staff:
            return None
        return {'email': obj.owner.email, 'first_name': obj.owner.first_name, 'last_name': obj.owner.last_name}

    def get_photo_count(self, obj):
        return obj.photos.count()


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for property view"""
    property_type_name = serializers.CharField(source='property_type.name', read_only=True)
    # Lets the owner edit form preselect the current type
    property_type_id = serializers.IntegerField(read_only=True, allow_null=True)
    booking_mode = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()
    photos = PropertyPhotoSerializer(many=True, read_only=True)
    cover_photo_url = serializers.SerializerMethodField()
    # Whole-property listings (Entry Villa) expose only their "Entire Villa"
    # unit here, so every consumer (guest page, admin review, search cards)
    # sees the villa itself rather than legacy owner-created rooms.
    room_types = serializers.SerializerMethodField()
    # Owner identity is only for the owner themself and admins - the detail
    # endpoint is also the public listing page (see _can_see_owner_identity).
    owner_email = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    contact = PropertyContactSerializer(read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True, allow_null=True)
    min_price = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'owner', 'owner_email', 'owner_name', 'property_type_id', 'property_type_name', 'booking_mode',
            'name', 'slug', 'description', 'short_description',
            'address', 'city', 'district', 'province', 'postal_code',
            'latitude', 'longitude', 'google_maps_url', 'nearby_attractions',
            'status', 'submitted_at', 'reviewed_at', 'reviewed_by', 'reviewed_by_name',
            'rejection_reason', 'house_rules', 'cover_photo_url', 'average_rating', 'total_reviews',
            'amenities', 'photos', 'room_types', 'contact', 'min_price',
            'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = [
            'id', 'slug', 'owner', 'average_rating', 'total_reviews',
            'created_at', 'updated_at', 'published_at', 'submitted_at', 'reviewed_at',
            'reviewed_by', 'reviewed_by_name'
        ]

    def get_min_price(self, obj):
        """
        Real starting-from price, computed the same way as
        PropertyCardSerializer.get_min_price (search results) - the lowest
        base_price across this property's room types. Property itself has no
        price_range_min/max fields; those don't exist on the model and
        shouldn't be invented just to satisfy the frontend. For Entry Villa it
        is the villa's own nightly price.
        """
        return starting_price_of(obj)

    def get_cover_photo_url(self, obj):
        return cover_url_of(obj)

    def get_booking_mode(self, obj):
        return booking_mode_of(obj)

    def get_room_types(self, obj):
        return RoomTypeListSerializer(bookable_room_types_of(obj), many=True, context=self.context).data

    def get_amenities(self, obj):
        amenities = obj.propertyamenity_set.all()
        return [
            {
                'id': pa.amenity.id,
                'name': pa.amenity.name,
                'slug': pa.amenity.slug,
                'icon_url': pa.amenity.icon_url,
                'category': pa.amenity.category
            }
            for pa in amenities
        ]

    def _can_see_owner_identity(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated and (user.is_staff or obj.owner_id == user.id))

    def get_owner_email(self, obj):
        return obj.owner.email if self._can_see_owner_identity(obj) else None

    def get_owner_name(self, obj):
        if not self._can_see_owner_identity(obj):
            return None
        return obj.owner.get_full_name() or obj.owner.email


class PropertyCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating properties"""
    amenity_ids = serializers.PrimaryKeyRelatedField(
        queryset=Amenity.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='amenities'
    )
    contact_phone = serializers.CharField(write_only=True, required=False, allow_blank=True)
    contact_email = serializers.EmailField(write_only=True, required=False, allow_blank=True)
    # Stored on the existing PropertyContact.whatsapp_number (digits only,
    # e.g. 94771234567); blank clears it. Returned via `contact` on the detail.
    whatsapp_number = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=30)

    class Meta:
        model = Property
        fields = [
            'id', 'property_type', 'name', 'description', 'short_description',
            'address', 'city', 'district', 'province', 'postal_code',
            'latitude', 'longitude', 'google_maps_url', 'nearby_attractions',
            'house_rules', 'cover_photo_url', 'amenity_ids', 'contact_phone', 'contact_email',
            'whatsapp_number', 'status'
        ]
        # cover_photo_url mirrors the chosen cover photo - change it via set-cover, never by URL
        read_only_fields = ['id', 'status', 'cover_photo_url']

    def validate_whatsapp_number(self, value):
        from apps.notifications.whatsapp import normalize_whatsapp_number
        if not value or not value.strip():
            return ''
        number = normalize_whatsapp_number(value)
        if number is None:
            raise serializers.ValidationError(
                'Enter a valid WhatsApp number in international format, e.g. +94771234567.'
            )
        return number

    def validate(self, attrs):
        if 'room_types' in self.initial_data:
            raise serializers.ValidationError({
                'room_types': 'Rooms must be created from the property room management endpoint.'
            })
        return attrs

    def create(self, validated_data):
        import logging
        from django.db import transaction

        logger = logging.getLogger(__name__)

        # Property creation is intentionally independent from room management.
        amenities = validated_data.pop('amenities', [])
        contact_phone = validated_data.pop('contact_phone', '')
        contact_email = validated_data.pop('contact_email', '')
        whatsapp_number = validated_data.pop('whatsapp_number', '')

        # Get current user from request context
        request = self.context.get('request')
        if request:
            validated_data['owner'] = request.user

        # Validate required fields
        if not validated_data.get('name'):
            raise serializers.ValidationError({'name': 'Property name is required'})
        if not validated_data.get('city'):
            raise serializers.ValidationError({'city': 'City is required'})
        if not validated_data.get('district'):
            raise serializers.ValidationError({'district': 'District is required'})
        if not validated_data.get('province'):
            raise serializers.ValidationError({'province': 'Province is required'})

        # Create the draft and its property-level relationships atomically.
        try:
            with transaction.atomic():
                # Create property
                property_obj = Property.objects.create(**validated_data)
                logger.info(f"Created property {property_obj.id}")

                # Add amenities
                if amenities:
                    PropertyAmenity.objects.bulk_create([
                        PropertyAmenity(property=property_obj, amenity=amenity)
                        for amenity in amenities
                    ])
                    logger.info(f"Added {len(amenities)} amenities to property {property_obj.id}")

                if contact_phone or contact_email or whatsapp_number:
                    PropertyContact.objects.create(
                        property=property_obj,
                        contact_phone=contact_phone,
                        email=contact_email,
                        whatsapp_number=whatsapp_number or None,
                    )

        except Exception as e:
            logger.error(f"Error in property creation transaction: {str(e)}", exc_info=True)
            raise serializers.ValidationError({
                'detail': f'Error creating property: {str(e)}'
            })

        return property_obj

    def update(self, instance, validated_data):
        from django.db import transaction

        # Room data is never accepted during a property update.
        amenities = validated_data.pop('amenities', None)
        contact_phone = validated_data.pop('contact_phone', None)
        contact_email = validated_data.pop('contact_email', None)
        whatsapp_number = validated_data.pop('whatsapp_number', None)

        with transaction.atomic():
            # Update property fields
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            # Update amenities if provided
            if amenities is not None:
                instance.propertyamenity_set.all().delete()
                PropertyAmenity.objects.bulk_create([
                    PropertyAmenity(property=instance, amenity=amenity)
                    for amenity in amenities
                ])

            if contact_phone is not None or contact_email is not None or whatsapp_number is not None:
                contact, _ = PropertyContact.objects.get_or_create(property=instance)
                if contact_phone is not None:
                    contact.contact_phone = contact_phone
                if contact_email is not None:
                    contact.email = contact_email
                if whatsapp_number is not None:
                    contact.whatsapp_number = whatsapp_number or None  # blank clears it
                contact.save()

        return instance


class PropertyApprovalSerializer(serializers.Serializer):
    """Serializer for property approval/rejection"""
    action = serializers.ChoiceField(choices=['approve', 'reject', 'suspend'])
    comments = serializers.CharField(required=False, allow_blank=True)

    def validate_action(self, value):
        if value not in ['approve', 'reject', 'suspend']:
            raise serializers.ValidationError(f"Invalid action: {value}")
        return value


class SeasonalRateSerializer(serializers.ModelSerializer):
    """Serializer for seasonal rates"""
    class Meta:
        model = SeasonalRate
        fields = [
            'id', 'room_type', 'name', 'price_per_night',
            'start_date', 'end_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PricingSerializer(serializers.ModelSerializer):
    """Serializer for room pricing"""
    seasonal_rates = SeasonalRateSerializer(many=True, read_only=True)

    class Meta:
        model = Pricing
        fields = [
            'id', 'room_type', 'base_price', 'weekend_price',
            'extra_guest_fee', 'child_fee', 'service_fee_percent', 'tax_percent',
            'currency', 'seasonal_rates', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PricingUpdateSerializer(serializers.Serializer):
    """
    Owner input for POST /api/properties/rooms/{id}/pricing/.

    Only owner-controlled prices are accepted; the platform's
    service_fee_percent / tax_percent / currency are never client input.
    base_price is required the first time pricing is created.
    """
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'), required=False)
    weekend_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01'), required=False, allow_null=True
    )
    extra_guest_fee = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0'), required=False, allow_null=True
    )
    child_fee = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0'), required=False, allow_null=True
    )


class PropertyCardSerializer(serializers.ModelSerializer):
    """Compact property card for search results"""
    property_type_name = serializers.CharField(source='property_type.name', read_only=True)
    amenities = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()
    room_count = serializers.SerializerMethodField()
    # The chosen cover photo (first photo as fallback) - no per-card image request
    cover_photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'slug', 'name', 'city', 'property_type_name',
            'cover_photo_url', 'average_rating', 'total_reviews',
            'amenities', 'min_price', 'room_count', 'short_description'
        ]

    def get_amenities(self, obj):
        """Get first 3 amenities for card display"""
        amenities = obj.propertyamenity_set.all()[:3]
        return [{'id': pa.amenity.id, 'name': pa.amenity.name} for pa in amenities]

    def get_min_price(self, obj):
        """Get minimum room price (the villa's own price for Entry Villa)"""
        return starting_price_of(obj)

    def get_cover_photo_url(self, obj):
        return cover_url_of(obj)

    def get_room_count(self, obj):
        """Get number of room types (1 - the villa itself - for Entry Villa)"""
        return bookable_room_types_of(obj).count()


class VillaDetailsSerializer(serializers.Serializer):
    """
    Owner input for an Entry Villa's villa-level details
    (PUT /api/properties/{id}/villa/). Stored on the system-managed
    "Entire Villa" RoomType + its Pricing, so booking, availability and search
    keep using the existing room-type architecture.
    """
    max_adults = serializers.IntegerField(min_value=1)
    max_children = serializers.IntegerField(min_value=0, default=0)
    total_occupancy = serializers.IntegerField(min_value=1, required=False)
    number_of_beds = serializers.IntegerField(min_value=1)
    bed_configuration = serializers.ChoiceField(choices=RoomType.BED_CONFIGURATION_CHOICES)
    bathroom_type = serializers.ChoiceField(choices=RoomType.BATHROOM_TYPE_CHOICES)
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    weekend_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0.01'), required=False, allow_null=True
    )

    def validate(self, attrs):
        # Same default as rooms: occupancy = adults + children unless given
        if attrs.get('total_occupancy') is None:
            attrs['total_occupancy'] = attrs['max_adults'] + attrs.get('max_children', 0)
        return attrs


class SearchFilterSerializer(serializers.Serializer):
    """Serializer for search filter options"""
    city = serializers.CharField(required=False)
    district = serializers.CharField(required=False)
    province = serializers.CharField(required=False)
    property_types = serializers.ListField(child=serializers.IntegerField(), required=False)
    amenities = serializers.ListField(child=serializers.IntegerField(), required=False)
    min_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    max_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    min_rating = serializers.FloatField(required=False)
    check_in = serializers.DateField(required=False)
    check_out = serializers.DateField(required=False)
    adults = serializers.IntegerField(required=False, min_value=1)
    children = serializers.IntegerField(required=False, min_value=0)
    search = serializers.CharField(required=False)
    sort_by = serializers.ChoiceField(
        choices=['newest', 'rating', 'price', 'name', 'reviews', 'popular'],
        required=False
    )
    sort_direction = serializers.ChoiceField(
        choices=['asc', 'desc'],
        required=False
    )
    page = serializers.IntegerField(required=False, min_value=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100)


class DestinationDetailSerializer(serializers.ModelSerializer):
    """Detailed destination with properties"""
    properties = serializers.SerializerMethodField()
    property_count = serializers.SerializerMethodField()

    class Meta:
        model = Destination
        fields = [
            'id', 'name', 'slug', 'description', 'cover_image_url',
            'city', 'district', 'province',
            'seo_title', 'seo_description', 'seo_keywords',
            'property_count', 'properties', 'is_published'
        ]

    def get_properties(self, obj):
        """Get first 12 properties in destination"""
        properties = Property.objects.filter(
            status='approved',
            city=obj.city
        )[:12]
        return PropertyCardSerializer(properties, many=True).data

    def get_property_count(self, obj):
        """Count published properties in destination"""
        return Property.objects.filter(
            status='approved',
            city=obj.city
        ).count()


class SearchResultsSerializer(serializers.Serializer):
    """Serializer for search results response"""
    count = serializers.IntegerField()
    next = serializers.URLField(required=False, allow_null=True)
    previous = serializers.URLField(required=False, allow_null=True)
    results = PropertyCardSerializer(many=True)
    filters_applied = serializers.DictField(required=False)

    class Meta:
        fields = ['count', 'next', 'previous', 'results', 'filters_applied']
