"""
Serializers for property management.
"""

from rest_framework import serializers
from .models import (
    PropertyType, Amenity, Destination, Property, PropertyPhoto,
    PropertyAmenity, RoomType, RoomTypePhoto, RoomTypeAmenity,
    Pricing, SeasonalRate
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


class RoomTypeListSerializer(serializers.ModelSerializer):
    """Serializer for room type list view"""
    amenities = serializers.SerializerMethodField()
    photos = RoomTypePhotoSerializer(many=True, read_only=True)

    class Meta:
        model = RoomType
        fields = [
            'id', 'name', 'slug', 'description', 'max_adults', 'max_children',
            'total_occupancy', 'bed_type', 'number_of_beds', 'total_rooms',
            'room_size_sqm', 'is_active', 'amenities', 'photos', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at']

    def get_amenities(self, obj):
        amenities = obj.roomatype.all()
        return RoomTypeAmenitySerializer(amenities, many=True).data


class RoomTypeDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for room type with all information"""
    amenities = serializers.SerializerMethodField()
    photos = RoomTypePhotoSerializer(many=True, read_only=True)

    class Meta:
        model = RoomType
        fields = [
            'id', 'property', 'name', 'slug', 'description',
            'max_adults', 'max_children', 'total_occupancy',
            'bed_type', 'number_of_beds', 'total_rooms', 'room_size_sqm',
            'is_active', 'amenities', 'photos', 'created_at', 'updated_at'
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
            'status', 'cover_photo_url', 'property_type_name', 'average_rating',
            'total_reviews', 'amenities', 'photo_count', 'created_at', 'published_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'published_at']

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

    class Meta:
        model = Property
        fields = [
            'id', 'owner', 'owner_email', 'owner_name', 'property_type_name',
            'name', 'slug', 'description', 'short_description',
            'address', 'city', 'district', 'province', 'postal_code',
            'latitude', 'longitude', 'google_maps_url',
            'status', 'cover_photo_url', 'average_rating', 'total_reviews',
            'amenities', 'photos', 'room_types',
            'created_at', 'updated_at', 'published_at'
        ]
        read_only_fields = [
            'id', 'slug', 'owner', 'average_rating', 'total_reviews',
            'created_at', 'updated_at', 'published_at'
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

    class Meta:
        model = Property
        fields = [
            'property_type', 'name', 'description', 'short_description',
            'address', 'city', 'district', 'province', 'postal_code',
            'latitude', 'longitude', 'google_maps_url',
            'cover_photo_url', 'amenity_ids'
        ]

    def create(self, validated_data):
        # Extract amenities (M2M) from validated data
        amenities = validated_data.pop('amenities', [])

        # Get current user from request context
        request = self.context.get('request')
        if request:
            validated_data['owner'] = request.user

        # Create property
        property_obj = Property.objects.create(**validated_data)

        # Add amenities
        if amenities:
            PropertyAmenity.objects.bulk_create([
                PropertyAmenity(property=property_obj, amenity=amenity)
                for amenity in amenities
            ])

        return property_obj

    def update(self, instance, validated_data):
        # Extract amenities (M2M) from validated data
        amenities = validated_data.pop('amenities', None)

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
