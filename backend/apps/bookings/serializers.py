"""
Serializers for booking management.
"""

from rest_framework import serializers
from datetime import date
from decimal import Decimal

from .models import Booking, BookingGuest, Availability
from apps.properties.models import RoomType, Property


class BookingGuestSerializer(serializers.ModelSerializer):
    """Serializer for booking guest information"""
    class Meta:
        model = BookingGuest
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'is_primary_guest']
        read_only_fields = ['id']


class AvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for room availability"""
    class Meta:
        model = Availability
        fields = ['id', 'room_type', 'date', 'status', 'available_count']
        read_only_fields = ['id']


class BookingListSerializer(serializers.ModelSerializer):
    """Serializer for booking list view"""
    property_name = serializers.CharField(source='property.name', read_only=True)
    room_type_name = serializers.CharField(source='room_type.name', read_only=True)
    guest_name = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_reference', 'property_name', 'room_type_name',
            'guest_name', 'check_in_date', 'check_out_date', 'number_of_nights',
            'total_price', 'status', 'payment_status', 'created_at'
        ]
        read_only_fields = fields

    def get_guest_name(self, obj):
        """Get primary guest name"""
        primary_guest = obj.guests.filter(is_primary_guest=True).first()
        if primary_guest:
            return f"{primary_guest.first_name} {primary_guest.last_name}"
        return obj.guest.get_full_name() or obj.guest.email


class BookingDetailSerializer(serializers.ModelSerializer):
    """Detailed booking serializer"""
    property_name = serializers.CharField(source='property.name', read_only=True)
    room_type_name = serializers.CharField(source='room_type.name', read_only=True)
    guests = BookingGuestSerializer(many=True, read_only=True)
    property_cover = serializers.URLField(source='property.cover_photo_url', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_reference', 'property_name', 'property_cover',
            'room_type_name', 'check_in_date', 'check_out_date', 'number_of_nights',
            'number_of_adults', 'number_of_children', 'number_of_rooms',
            'room_price', 'subtotal', 'discount', 'service_fee', 'tax', 'total_price',
            'special_requests', 'guests', 'status', 'payment_status',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class BookingCreateSerializer(serializers.Serializer):
    """Serializer for creating bookings"""
    room_type_id = serializers.UUIDField()
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    number_of_adults = serializers.IntegerField(min_value=1, default=1)
    number_of_children = serializers.IntegerField(min_value=0, default=0)
    number_of_rooms = serializers.IntegerField(min_value=1, default=1)
    guests = BookingGuestSerializer(many=True, required=False)
    special_requests = serializers.CharField(required=False, allow_blank=True)
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, default=Decimal('0')
    )
    discount_fixed = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, default=Decimal('0')
    )

    def validate_check_in_date(self, value):
        """Validate check-in date is not in past"""
        if value < date.today():
            raise serializers.ValidationError("Check-in date cannot be in the past")
        return value

    def validate(self, data):
        """Validate date range and occupancy"""
        check_in = data['check_in_date']
        check_out = data['check_out_date']

        if check_in >= check_out:
            raise serializers.ValidationError(
                "Check-out date must be after check-in date"
            )

        # Validate room type exists
        try:
            room_type = RoomType.objects.get(id=data['room_type_id'])
        except RoomType.DoesNotExist:
            raise serializers.ValidationError("Invalid room type")

        # Validate occupancy
        total_occupants = data['number_of_adults'] + data['number_of_children']
        if data['number_of_adults'] > room_type.max_adults:
            raise serializers.ValidationError(
                f"Room can accommodate maximum {room_type.max_adults} adults"
            )

        if total_occupants > room_type.total_occupancy:
            raise serializers.ValidationError(
                f"Room can accommodate maximum {room_type.total_occupancy} guests"
            )

        return data


class BookingCancelSerializer(serializers.Serializer):
    """Serializer for cancelling bookings"""
    reason = serializers.CharField(required=False, allow_blank=True)


class PriceCalculationSerializer(serializers.Serializer):
    """Serializer for price calculation request"""
    room_type_id = serializers.UUIDField()
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    number_of_adults = serializers.IntegerField(min_value=1, default=1)
    number_of_children = serializers.IntegerField(min_value=0, default=0)
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, default=Decimal('0')
    )
    discount_fixed = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=0, default=Decimal('0')
    )


class PriceBreakdownSerializer(serializers.Serializer):
    """Serializer for price breakdown response"""
    nights = serializers.IntegerField()
    room_price_per_night = serializers.DecimalField(max_digits=12, decimal_places=2)
    room_subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    guest_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2)
    service_fee = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax = serializers.DecimalField(max_digits=12, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    date_breakdown = serializers.ListField(child=serializers.DictField())


class AvailabilityCheckSerializer(serializers.Serializer):
    """Serializer for availability check"""
    room_type_id = serializers.UUIDField()
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()


class AvailabilityResponseSerializer(serializers.Serializer):
    """Serializer for availability check response"""
    is_available = serializers.BooleanField()
    available_count = serializers.IntegerField()
    room_type_id = serializers.UUIDField()
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()


class AdminBookingListSerializer(serializers.ModelSerializer):
    """Serializer for admin booking list view with owner details"""
    property_name = serializers.CharField(source='property.name', read_only=True)
    property_owner = serializers.CharField(source='property.owner.get_full_name', read_only=True)
    property_owner_email = serializers.CharField(source='property.owner.email', read_only=True)
    room_type_name = serializers.CharField(source='room_type.name', read_only=True)
    guest_name = serializers.SerializerMethodField()
    guest_email = serializers.CharField(source='guest.email', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_reference', 'property_name', 'property_owner', 'property_owner_email',
            'room_type_name', 'guest_name', 'guest_email', 'check_in_date', 'check_out_date',
            'number_of_nights', 'total_price', 'status', 'payment_status', 'created_at'
        ]
        read_only_fields = fields

    def get_guest_name(self, obj):
        """Get primary guest name"""
        primary_guest = obj.guests.filter(is_primary_guest=True).first()
        if primary_guest:
            return f"{primary_guest.first_name} {primary_guest.last_name}"
        return obj.guest.get_full_name() or obj.guest.email
