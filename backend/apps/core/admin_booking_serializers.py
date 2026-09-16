"""
Serializers for admin booking and payment operations.
"""

from rest_framework import serializers
from apps.bookings.models import Booking, BookingGuest
from apps.payments.models import Payment, Refund
from apps.properties.models import Property


class AdminBookingGuestSerializer(serializers.ModelSerializer):
    """Serializer for booking guest details"""
    class Meta:
        model = BookingGuest
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'is_primary_guest']
        read_only_fields = fields


class AdminPaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment information in booking detail"""
    class Meta:
        model = Payment
        fields = [
            'id', 'amount', 'status', 'payment_method',
            'transaction_reference', 'gateway_name', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class AdminRefundSerializer(serializers.ModelSerializer):
    """Serializer for refund information"""
    class Meta:
        model = Refund
        fields = [
            'id', 'amount', 'reason', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class AdminBookingDetailSerializer(serializers.ModelSerializer):
    """Detailed booking serializer for admin operations"""
    property_name = serializers.CharField(source='property.name', read_only=True)
    property_owner = serializers.CharField(source='property.owner.get_full_name', read_only=True)
    property_owner_email = serializers.CharField(source='property.owner.email', read_only=True)
    room_type_name = serializers.CharField(source='room_type.name', read_only=True)
    guest_name = serializers.CharField(source='guest.get_full_name', read_only=True)
    guest_email = serializers.CharField(source='guest.email', read_only=True)
    guest_phone = serializers.CharField(source='guest.phone', read_only=True)
    guests = AdminBookingGuestSerializer(many=True, read_only=True)
    payments = AdminPaymentSerializer(many=True, read_only=True)
    refunds = AdminRefundSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'booking_reference', 'property_name', 'property_owner', 'property_owner_email',
            'room_type_name', 'guest_name', 'guest_email', 'guest_phone',
            'check_in_date', 'check_out_date', 'number_of_nights',
            'number_of_adults', 'number_of_children', 'number_of_rooms',
            'room_price', 'subtotal', 'discount', 'service_fee', 'tax', 'total_price',
            'special_requests', 'guests', 'status', 'payment_status',
            'payments', 'refunds', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class AdminBookingStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating booking status"""
    status = serializers.ChoiceField(
        choices=Booking.STATUS_CHOICES,
        help_text="New booking status"
    )

    def validate_status(self, value):
        """Validate that status is allowed"""
        valid_statuses = [choice[0] for choice in Booking.STATUS_CHOICES]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {valid_statuses}")
        return value


class AdminBookingCancelSerializer(serializers.Serializer):
    """Serializer for admin booking cancellation"""
    reason = serializers.CharField(required=False, allow_blank=True, default='admin_request')


class AdminPaymentListSerializer(serializers.ModelSerializer):
    """Serializer for payment list in admin view"""
    booking_reference = serializers.CharField(source='booking.booking_reference', read_only=True)
    guest_email = serializers.CharField(source='booking.guest.email', read_only=True)
    guest_name = serializers.CharField(source='booking.guest.get_full_name', read_only=True)
    property_name = serializers.CharField(source='booking.property.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'booking_reference', 'property_name', 'guest_name', 'guest_email',
            'amount', 'status', 'payment_method', 'transaction_reference',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class AdminPaymentDetailSerializer(serializers.ModelSerializer):
    """Detailed payment serializer for admin operations"""
    booking_reference = serializers.CharField(source='booking.booking_reference', read_only=True)
    booking_id = serializers.CharField(source='booking.id', read_only=True)
    guest_email = serializers.CharField(source='booking.guest.email', read_only=True)
    guest_name = serializers.CharField(source='booking.guest.get_full_name', read_only=True)
    property_name = serializers.CharField(source='booking.property.name', read_only=True)
    property_owner_email = serializers.CharField(source='booking.property.owner.email', read_only=True)
    refunds = AdminRefundSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'booking_reference', 'booking_id', 'property_name',
            'guest_name', 'guest_email', 'property_owner_email',
            'amount', 'status', 'payment_method', 'transaction_reference',
            'gateway_name', 'error_message', 'refunds',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class AdminRefundRequestSerializer(serializers.Serializer):
    """Serializer for requesting a refund"""
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        required=False,
        help_text="Refund amount (if empty, uses payment amount)"
    )
    reason = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Reason for refund"
    )

    def validate_amount(self, value):
        """Validate refund amount is positive"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Refund amount must be greater than 0")
        return value
