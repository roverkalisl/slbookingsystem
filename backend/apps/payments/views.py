"""
Views for payment processing and management.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from decimal import Decimal

from .models import Payment, Refund
from .serializers import (
    PaymentSerializer, PaymentInitiateSerializer,
    PaymentConfirmSerializer, RefundSerializer, RefundRequestSerializer
)
from .service import PaymentService, PaymentWebhookHandler
from apps.bookings.models import Booking
from apps.notifications.service import NotificationService


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for payment processing.

    Endpoints:
    - POST /api/payments/initiate/ - Initiate payment
    - POST /api/payments/{id}/confirm/ - Confirm payment
    - POST /api/payments/{id}/refund/ - Refund payment
    - GET /api/payments/{id}/ - Payment details
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        """Get payments for current user"""
        user = self.request.user

        if user.is_staff:
            return Payment.objects.all()

        # Guests see their own payments
        if user.has_role('guest'):
            return Payment.objects.filter(booking__guest=user)

        # Owners see payment for their properties
        if user.has_role('property_owner'):
            return Payment.objects.filter(booking__property__owner=user)

        return Payment.objects.none()

    @action(detail=False, methods=['post'])
    def initiate(self, request):
        """
        Initiate payment for a booking.

        POST /api/payments/initiate/
        {
            "booking_id": "uuid",
            "payment_method": "stripe"
        }
        """
        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            booking = Booking.objects.get(id=serializer.validated_data['booking_id'])

            # Permission check
            if booking.guest != request.user and not request.user.is_staff:
                raise PermissionDenied("You can only pay for your own bookings")

            # Initiate payment
            result = PaymentService.initiate_payment(
                booking,
                serializer.validated_data['payment_method']
            )

            return Response(
                {
                    'success': True,
                    'message': 'Payment initiated',
                    'data': result
                },
                status=status.HTTP_200_OK
            )

        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Confirm payment.

        POST /api/payments/{id}/confirm/
        {
            "transaction_reference": "TXN-123456",
            "status": "paid"
        }
        """
        try:
            payment = Payment.objects.get(id=pk)

            # Permission check
            if payment.booking.guest != request.user and not request.user.is_staff:
                raise PermissionDenied("You cannot confirm this payment")

            serializer = PaymentConfirmSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Confirm payment
            result = PaymentService.confirm_payment(
                payment,
                request.data.get('transaction_reference', {})
            )

            # Send confirmation email
            NotificationService.send_payment_confirmation(
                payment.booking,
                payment.amount
            )

            return Response(
                {
                    'success': True,
                    'message': 'Payment confirmed',
                    'data': result
                },
                status=status.HTTP_200_OK
            )

        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """
        Refund a payment.

        POST /api/payments/{id}/refund/
        {
            "amount": "5000.00",
            "reason": "Guest cancellation"
        }
        """
        try:
            payment = Payment.objects.get(id=pk)

            # Permission check
            if payment.booking.property.owner != request.user and not request.user.is_staff:
                raise PermissionDenied("You cannot refund this payment")

            serializer = RefundRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            amount = serializer.validated_data.get('amount')
            reason = serializer.validated_data.get('reason', 'Guest cancellation')

            # Process refund
            result = PaymentService.process_refund(payment, amount)

            # Send refund notification
            # NotificationService.send_refund_notification(payment.booking, amount)

            return Response(
                {
                    'success': True,
                    'message': 'Refund processed',
                    'data': result
                },
                status=status.HTTP_200_OK
            )

        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class PaymentWebhookViewSet(viewsets.ViewSet):
    """Handle payment webhooks from gateways"""

    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'])
    def stripe(self, request):
        """
        Handle Stripe webhook.

        POST /api/payments/webhook/stripe/
        """
        result = PaymentWebhookHandler.handle_webhook(
            'stripe',
            request.data
        )

        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def bank_transfer(self, request):
        """
        Handle bank transfer webhook.

        POST /api/payments/webhook/bank-transfer/
        """
        result = PaymentWebhookHandler.handle_webhook(
            'bank_transfer',
            request.data
        )

        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
