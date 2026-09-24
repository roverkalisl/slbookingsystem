"""
Views for payment processing and management.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from decimal import Decimal

from .models import Payment, Refund
from .serializers import (
    PaymentSerializer, PaymentInitiateSerializer,
    PaymentConfirmSerializer, RefundSerializer, RefundRequestSerializer
)
from .service import (
    PaymentService, PaymentWebhookHandler, PaymentGatewayError,
    ManualConfirmationNotAllowed, send_payment_confirmation_email,
)
from apps.bookings.models import Booking
import logging

logger = logging.getLogger(__name__)


def _find_payment(pk):
    """Payment by id, or None for a missing or malformed id (-> 404, not 500)."""
    try:
        return Payment.objects.get(id=pk)
    except (Payment.DoesNotExist, DjangoValidationError):
        return None


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for payment processing.

    Endpoints:
    - POST /api/payments/initiate/ - Initiate payment
    - POST /api/payments/{id}/confirm/ - Confirm payment
    - POST /api/payments/{id}/refund/ - Refund payment
    - GET /api/payments/{id}/ - Payment details

    Payment records are financial audit data: read-only through the generic
    routes (no create/update/delete). All state changes go through the
    explicit actions above, which apply server-side rules.
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
        except ValueError as e:
            # Booking not payable (cancelled/rejected/already paid)
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)
        except PaymentGatewayError as e:
            # Stripe unavailable/unconfigured - nothing was saved (rolled back)
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

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
            payment = _find_payment(pk)
            if payment is None:
                return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

            # Permission check: the guest must NOT be able to mark their own
            # payment as paid (that would also confirm their booking without
            # the owner or any real payment). Offline payments (pay-at-property,
            # bank transfer) are confirmed by the property owner or an admin -
            # the same rule as POST /api/bookings/{id}/confirm_payment/.
            if payment.booking.property.owner != request.user and not request.user.is_staff:
                raise PermissionDenied("Only the property owner or an admin can confirm this payment")

            serializer = PaymentConfirmSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Record the requested outcome - 'failed'/'cancelled' never mark
            # the payment paid or confirm the booking.
            outcome = serializer.validated_data['status']
            reference = serializer.validated_data.get('transaction_reference')
            result = PaymentService.confirm_payment(
                payment,
                {'transaction_reference': reference} if reference else {},
                status=outcome
            )

            # Send confirmation email only for a newly confirmed payment (not on
            # an idempotent repeat). Failures are logged; the payment stays saved.
            if outcome == 'paid' and result.get('message') == 'Payment confirmed':
                payment.refresh_from_db()
                send_payment_confirmation_email(payment)

            return Response(
                {
                    'success': True,
                    'message': result['message'],
                    'data': result
                },
                status=status.HTTP_200_OK
            )

        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ManualConfirmationNotAllowed as e:
            # Card payments are settled only by verified Stripe webhooks
            return Response({'error': str(e)}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_409_CONFLICT)

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
            payment = _find_payment(pk)
            if payment is None:
                return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

            # Permission check: property owner (own properties only) or admin.
            # Guests can never initiate refunds.
            if payment.booking.property.owner != request.user and not request.user.is_staff:
                raise PermissionDenied("You cannot refund this payment")

            serializer = RefundRequestSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            amount = serializer.validated_data.get('amount')
            reason = serializer.validated_data.get('reason') or 'Guest cancellation'

            # Process refund - the service enforces amount <= paid - already refunded
            try:
                result = PaymentService.process_refund(payment, amount, reason=reason)
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except PaymentGatewayError as e:
                # Stripe refused/failed - no refund recorded (rolled back)
                return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

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

    # Webhooks are authenticated by the gateway signature, not by a user
    # session/JWT. Not throttled: Stripe delivers bursts and retries, and
    # every request is signature-checked before any state change.
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    @action(detail=False, methods=['post'])
    def stripe(self, request):
        """
        Handle Stripe webhook.

        POST /api/payments/webhook/stripe/

        Verified with the official SDK (stripe.Webhook.construct_event) over
        the RAW request body and the Stripe-Signature header. request.data is
        deliberately never touched - re-serialized JSON would not match the
        signature.
        """
        http_status, result = PaymentWebhookHandler.handle_stripe_webhook(
            request.body,
            request.META.get('HTTP_STRIPE_SIGNATURE')
        )
        return Response(result, status=http_status)

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
