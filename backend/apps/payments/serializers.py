"""
Serializers for payment management.
"""

from decimal import Decimal

from rest_framework import serializers
from .models import Payment, Refund


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment information"""
    booking_reference = serializers.CharField(source='booking.booking_reference', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'booking', 'booking_reference', 'amount', 'status',
            'payment_method', 'transaction_reference', 'gateway_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields


class PaymentInitiateSerializer(serializers.Serializer):
    """Serializer for initiating payment"""
    booking_id = serializers.UUIDField()
    payment_method = serializers.ChoiceField(
        choices=['stripe', 'pay_at_property', 'bank_transfer'],
        default='stripe'
    )


class PaymentConfirmSerializer(serializers.Serializer):
    """Serializer for confirming payment"""
    transaction_reference = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=['paid', 'failed', 'cancelled'])


class RefundSerializer(serializers.ModelSerializer):
    """Serializer for refund information"""
    class Meta:
        model = Refund
        fields = [
            'id', 'booking', 'payment', 'amount', 'reason',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class RefundRequestSerializer(serializers.Serializer):
    """Serializer for refund request"""
    # Optional: omitted = refund the full remaining refundable balance.
    # Never trusted on its own - PaymentService.validate_refund_amount caps it
    # at (amount paid - already refunded).
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        required=False, min_value=Decimal('0.01')
    )
    reason = serializers.CharField(required=False, allow_blank=True)
