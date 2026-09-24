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
    property_id = serializers.UUIDField(source='property.id', read_only=True)
    room_type_name = serializers.CharField(source='room_type.name', read_only=True)
    guest_name = serializers.SerializerMethodField()
    guest_email = serializers.SerializerMethodField()
    guest_phone = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_reference', 'property_id', 'property_name', 'room_type_name',
            'guest_name', 'guest_email', 'guest_phone', 'number_of_adults', 'number_of_children',
            'check_in_date', 'check_out_date', 'number_of_nights',
            'total_price', 'status', 'payment_status', 'created_at'
        ]
        read_only_fields = fields

    def get_guest_name(self, obj):
        """Get primary guest name"""
        primary_guest = obj.guests.filter(is_primary_guest=True).first()
        if primary_guest:
            return f"{primary_guest.first_name} {primary_guest.last_name}"
        return obj.guest.get_full_name() or obj.guest.email

    def get_guest_email(self, obj):
        """
        Contact info exposed here only because the queryset is already
        ownership-filtered upstream (BookingViewSet.get_queryset): owners
        only ever see bookings for their own properties, guests only their
        own bookings, so no cross-user leak is possible through this field.
        """
        primary_guest = obj.guests.filter(is_primary_guest=True).first()
        if primary_guest and primary_guest.email:
            return primary_guest.email
        return obj.guest.email

    def get_guest_phone(self, obj):
        primary_guest = obj.guests.filter(is_primary_guest=True).first()
        if primary_guest and primary_guest.phone:
            return primary_guest.phone
        return obj.guest.phone


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
    """
    Serializer for creating bookings.

    SECURITY: accepts only what the guest legitimately chooses (room, dates,
    guest counts, room count, guest details, requests). No financial field -
    discount_percent, discount_fixed, subtotal, discount, tax, service_fee,
    total_price, room_price - is declared, so any such values sent by a client
    are ignored. BookingService/PricingCalculator compute the authoritative
    price server-side.
    """
    room_type_id = serializers.UUIDField()
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    number_of_adults = serializers.IntegerField(min_value=1, default=1)
    number_of_children = serializers.IntegerField(min_value=0, default=0)
    number_of_rooms = serializers.IntegerField(min_value=1, default=1)
    guests = BookingGuestSerializer(many=True, required=False)
    special_requests = serializers.CharField(required=False, allow_blank=True)

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

        # Validate occupancy against the combined capacity of all requested
        # rooms (limits are per room; BookingService applies the same rule).
        num_rooms = data.get('number_of_rooms', 1)
        total_occupants = data['number_of_adults'] + data['number_of_children']
        max_adults = room_type.max_adults * num_rooms
        max_children = room_type.max_children * num_rooms
        max_occupancy = room_type.total_occupancy * num_rooms
        rooms_label = "Room" if num_rooms == 1 else f"{num_rooms} rooms"
        if data['number_of_adults'] > max_adults:
            raise serializers.ValidationError(
                f"{rooms_label} can accommodate maximum {max_adults} adults"
            )

        if data['number_of_children'] > max_children:
            raise serializers.ValidationError(
                f"{rooms_label} can accommodate maximum {max_children} children"
            )

        if total_occupants > max_occupancy:
            raise serializers.ValidationError(
                f"{rooms_label} can accommodate maximum {max_occupancy} guests"
            )

        return data


class BookingCancelSerializer(serializers.Serializer):
    """Serializer for cancelling bookings"""
    reason = serializers.CharField(required=False, allow_blank=True)


class PriceCalculationSerializer(serializers.Serializer):
    """
    Serializer for price calculation request.

    Mirrors BookingCreateSerializer so the quoted price is exactly what a
    booking would store - no client-supplied discount is accepted.
    """
    room_type_id = serializers.UUIDField()
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    number_of_adults = serializers.IntegerField(min_value=1, default=1)
    number_of_children = serializers.IntegerField(min_value=0, default=0)
    number_of_rooms = serializers.IntegerField(min_value=1, default=1)


class PriceBreakdownSerializer(serializers.Serializer):
    """Serializer for price breakdown response"""
    nights = serializers.IntegerField()
    num_rooms = serializers.IntegerField()
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
