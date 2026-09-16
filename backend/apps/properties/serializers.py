"""
Serializers for property management.
"""

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
        fields = ['id', 'name', 'description', 'is_active']
        read_only_fields = ['id']


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
            'name', 'description', 'room_type', 'max_adults', 'max_children',
            'bed_configuration', 'bathroom_type', 'number_of_beds', 'total_rooms',
            'room_size_sqft', 'view_type', 'amenity_ids'
        ]


class RoomTypeListSerializer(serializers.ModelSerializer):
    """Serializer for room type list view"""
    amenities = serializers.SerializerMethodField()
    photos = RoomTypePhotoSerializer(many=True, read_only=True)

    class Meta:
        model = RoomType
        fields = [
            'id', 'name', 'slug', 'description', 'room_type', 'max_adults', 'max_children',
            'total_occupancy', 'bed_configuration', 'bathroom_type', 'number_of_beds', 'total_rooms',
            'room_size_sqft', 'view_type', 'is_active', 'amenities', 'photos', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at']

    def get_amenities(self, obj):
        amenities = obj.roomatypeamenity_set.all()
        return RoomTypeAmenitySerializer(amenities, many=True).data


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
            'view_type', 'is_active', 'amenities', 'photos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

    def get_amenities(self, obj):
        amenities = obj.roomatypeamenity_set.all()
        return RoomTypeAmenitySerializer(amenities, many=True).data


class PropertyListSerializer(serializers.ModelSerializer):
    """Serializer for property list view"""
    property_type_name = serializers.CharField(source='property_type.name', read_only=True)
    amenities = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'name', 'slug', 'short_description', 'city', 'district',
            'status', 'submitted_at', 'rejection_reason', 'house_rules',
            'cover_photo_url', 'property_type_name', 'average_rating',
            'total_reviews', 'amenities', 'photo_count', 'created_at', 'published_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'published_at', 'submitted_at']

    def get_amenities(self, obj):
        amenities = obj.propertyamenity_set.all()[:5]  # Show first 5
        return [{'name': pa.amenity.name, 'slug': pa.amenity.slug} for pa in amenities]

    def get_photo_count(self, obj):
        return obj.photos.count()


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for property view"""
    property_type_name = serializers.CharField(source='property_type.name', read_only=True)
    amenities = serializers.SerializerMethodField()
    photos = PropertyPhotoSerializer(many=True, read_only=True)
    room_types = RoomTypeListSerializer(many=True, read_only=True)
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    owner_name = serializers.SerializerMethodField()
    contact = PropertyContactSerializer(read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True, allow_null=True)

    class Meta:
        model = Property
        fields = [
            'id', 'owner', 'owner_email', 'owner_name', 'property_type_name',
            'name', 'slug', 'description', 'short_description',
            'address', 'city', 'district', 'province', 'postal_code',
            'latitude', 'longitude', 'google_maps_url', 'nearby_attractions',
            'status', 'submitted_at', 'reviewed_at', 'reviewed_by', 'reviewed_by_name',
            'rejection_reason', 'house_rules', 'cover_photo_url', 'average_rating', 'total_reviews',
            'amenities', 'photos', 'room_types', 'contact',
            'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = [
            'id', 'slug', 'owner', 'average_rating', 'total_reviews',
            'created_at', 'updated_at', 'published_at', 'submitted_at', 'reviewed_at',
            'reviewed_by', 'reviewed_by_name'
        ]

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

    def get_owner_name(self, obj):
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
    room_types = RoomTypeCreateSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Property
        fields = [
            'id', 'property_type', 'name', 'description', 'short_description',
            'address', 'city', 'district', 'province', 'postal_code',
            'latitude', 'longitude', 'google_maps_url', 'nearby_attractions',
            'house_rules', 'cover_photo_url', 'amenity_ids', 'room_types', 'status'
        ]
        read_only_fields = ['id', 'status']

    def create(self, validated_data):
        from django.db import transaction

        # Extract M2M and nested data
        amenities = validated_data.pop('amenities', [])
        room_types_data = validated_data.pop('room_types', [])

        # Get current user from request context
        request = self.context.get('request')
        if request:
            validated_data['owner'] = request.user

        # Create property and room types within transaction
        with transaction.atomic():
            # Create property
            property_obj = Property.objects.create(**validated_data)

            # Add amenities
            if amenities:
                PropertyAmenity.objects.bulk_create([
                    PropertyAmenity(property=property_obj, amenity=amenity)
                    for amenity in amenities
                ])

            # Create room types
            for room_data in room_types_data:
                room_amenities = room_data.pop('amenities', [])
                room_obj = RoomType.objects.create(property=property_obj, **room_data)

                # Add room amenities
                if room_amenities:
                    RoomTypeAmenity.objects.bulk_create([
                        RoomTypeAmenity(room_type=room_obj, amenity=amenity)
                        for amenity in room_amenities
                    ])

        return property_obj

    def update(self, instance, validated_data):
        from django.db import transaction

        # Extract M2M and nested data
        amenities = validated_data.pop('amenities', None)
        room_types_data = validated_data.pop('room_types', None)

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

            # Update room types if provided
            if room_types_data is not None:
                instance.room_types.all().delete()
                for room_data in room_types_data:
                    room_amenities = room_data.pop('amenities', [])
                    room_obj = RoomType.objects.create(property=instance, **room_data)

                    if room_amenities:
                        RoomTypeAmenity.objects.bulk_create([
                            RoomTypeAmenity(room_type=room_obj, amenity=amenity)
                            for amenity in room_amenities
                        ])

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


class PropertyCardSerializer(serializers.ModelSerializer):
    """Compact property card for search results"""
    property_type_name = serializers.CharField(source='property_type.name', read_only=True)
    amenities = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()
    room_count = serializers.SerializerMethodField()

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
        """Get minimum room price"""
        min_price = obj.room_types.aggregate(
            min=models.Min('pricing__base_price')
        )['min']
        return str(min_price) if min_price else None

    def get_room_count(self, obj):
        """Get number of room types"""
        return obj.room_types.count()


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
            status='published',
            city=obj.city
        )[:12]
        return PropertyCardSerializer(properties, many=True).data

    def get_property_count(self, obj):
        """Count published properties in destination"""
        return Property.objects.filter(
            status='published',
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
