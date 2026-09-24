"""
Admin views for booking and payment operations.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db import transaction

from apps.bookings.models import Booking, BookingGuest
from apps.bookings.service import BookingService
from apps.payments.service import PaymentService
from apps.payments.models import Payment, Refund
from .permissions import IsAdminUser
from .admin_booking_serializers import (
    AdminBookingDetailSerializer,
    AdminBookingStatusUpdateSerializer,
    AdminBookingCancelSerializer,
    AdminPaymentListSerializer,
    AdminPaymentDetailSerializer,
    AdminRefundRequestSerializer,
    AdminRefundSerializer,
)


class AdminBookingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin booking operations ViewSet.

    Endpoints:
    - GET /api/admin/bookings/{id}/ - Booking details
    - PATCH /api/admin/bookings/{id}/status/ - Update booking status
    - POST /api/admin/bookings/{id}/cancel/ - Cancel booking
    """

    permission_classes = [IsAdminUser]
    queryset = Booking.objects.all().select_related(
        'property', 'room_type', 'guest', 'property__owner'
    ).prefetch_related('guests', 'payments', 'refund_set')  # Refund.booking has no related_name
    serializer_class = AdminBookingDetailSerializer
    lookup_field = 'id'

    def get_serializer_class(self):
        """Choose serializer based on action"""
        if self.action == 'update_status':
            return AdminBookingStatusUpdateSerializer
        elif self.action == 'cancel':
            return AdminBookingCancelSerializer
        return AdminBookingDetailSerializer

    @action(detail=True, methods=['patch', 'post'])
    def status(self, request, id=None):
        """
        Update booking status.

        PATCH /api/admin/bookings/{id}/status/
        {
            "status": "confirmed"
        }
        """
        booking = self.get_object()
        serializer = AdminBookingStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data['status']

        with transaction.atomic():
            # Lock and re-read so the transition is validated against current state
            booking = Booking.objects.select_for_update().get(id=booking.id)
            response = self._apply_status_transition(booking, new_status)

        return response

    def _apply_status_transition(self, booking, new_status):
        """Validate and apply an admin status change (caller holds the row lock)."""
        # Validate status transition
        current_status = booking.status

        # Define valid transitions
        valid_transitions = {
            'pending': ['confirmed', 'cancelled', 'rejected'],
            'confirmed': ['payment_pending', 'completed', 'cancelled'],
            'payment_pending': ['paid', 'cancelled', 'rejected'],
            'paid': ['completed', 'cancelled'],
            'completed': [],
            'cancelled': [],
            'rejected': [],
            'no_show': [],
            'refunded': [],
            'partially_refunded': [],
        }

        if new_status not in valid_transitions.get(current_status, []):
            return Response(
                {
                    'error': f'Cannot transition from {current_status} to {new_status}',
                    'valid_transitions': valid_transitions.get(current_status, [])
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        booking.status = new_status
        booking.save()

        # Every allowed transition into cancelled/rejected comes from a status
        # that held inventory, so release the rooms from the daily count.
        if new_status in ('cancelled', 'rejected'):
            BookingService._update_availability(
                booking.room_type, booking.check_in_date, booking.check_out_date,
                'available', booking.number_of_rooms
            )

        return Response(
            {
                'success': True,
                'message': f'Booking status updated to {new_status}',
                'data': AdminBookingDetailSerializer(booking).data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def cancel(self, request, id=None):
        """
        Cancel booking (admin override).

        POST /api/admin/bookings/{id}/cancel/
        {
            "reason": "Admin cancellation"
        }
        """
        booking = self.get_object()
        serializer = AdminBookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check if booking is already cancelled
        if booking.status == 'cancelled':
            return Response(
                {'error': 'Booking is already cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if booking can be cancelled
        if booking.status not in ['pending', 'confirmed', 'payment_pending', 'paid']:
            return Response(
                {'error': f'Cannot cancel booking with status: {booking.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = serializer.validated_data.get('reason', 'admin_request')

        # Cancel booking within transaction
        with transaction.atomic():
            booking = Booking.objects.select_for_update().get(id=booking.id)
            # Re-check under the lock so a concurrent cancel can't release rooms twice
            if booking.status not in ['pending', 'confirmed', 'payment_pending', 'paid']:
                return Response(
                    {'error': f'Cannot cancel booking with status: {booking.status}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            booking.status = 'cancelled'
            booking.save()

            # Keep the daily availability count in sync (same as guest cancel/owner reject)
            BookingService._update_availability(
                booking.room_type, booking.check_in_date, booking.check_out_date,
                'available', booking.number_of_rooms
            )

        return Response(
            {
                'success': True,
                'message': f'Booking cancelled (reason: {reason})',
                'data': AdminBookingDetailSerializer(booking).data
            },
            status=status.HTTP_200_OK
        )


class AdminPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin payment operations ViewSet.

    Endpoints:
    - GET /api/admin/payments/ - List all payments
    - GET /api/admin/payments/{id}/ - Payment details
    - POST /api/admin/payments/{id}/request-refund/ - Request refund
    """

    permission_classes = [IsAdminUser]
    queryset = Payment.objects.all().select_related(
        'booking', 'booking__property', 'booking__guest', 'booking__property__owner'
    ).prefetch_related('refunds')
    serializer_class = AdminPaymentDetailSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'payment_method']
    search_fields = ['booking__booking_reference', 'booking__guest__email', 'transaction_reference']
    ordering_fields = ['created_at', 'amount', 'status']
    ordering = ['-created_at']
    lookup_field = 'id'

    def get_serializer_class(self):
        """Choose serializer based on action"""
        if self.action == 'list':
            return AdminPaymentListSerializer
        elif self.action == 'request_refund':
            return AdminRefundRequestSerializer
        return AdminPaymentDetailSerializer

    @action(detail=True, methods=['post'])
    def request_refund(self, request, id=None):
        """
        Request a refund for a payment.

        POST /api/admin/payments/{id}/request-refund/
        {
            "amount": 100.00,
            "reason": "Guest requested cancellation"
        }
        """
        payment = self.get_object()
        serializer = AdminRefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data.get('reason', 'Admin refund')

        # Create refund record
        with transaction.atomic():
            # Lock the payment and apply the shared server-side limit:
            # amount <= paid - already refunded (cumulative, not per request).
            payment = Payment.objects.select_for_update().get(id=payment.id)
            try:
                amount = PaymentService.validate_refund_amount(
                    payment, serializer.validated_data.get('amount')
                )
            except ValueError as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            refund = Refund.objects.create(
                booking=payment.booking,
                payment=payment,
                amount=amount,
                reason=reason,
                status='pending'
            )

            # Update payment status from the cumulative refunded total
            if PaymentService.refundable_amount(payment) <= 0:
                payment.status = 'refunded'
            else:
                payment.status = 'partially_refunded'
            payment.save()

        return Response(
            {
                'success': True,
                'message': f'Refund request created: {amount} {reason}',
                'data': {
                    'refund_id': str(refund.id),
                    'amount': str(refund.amount),
                    'status': refund.status,
                    'payment_id': str(payment.id),
                    'booking_reference': payment.booking.booking_reference
                }
            },
            status=status.HTTP_201_CREATED
        )


class AdminRefundViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin refund operations ViewSet.

    Endpoints:
    - GET /api/admin/refunds/ - List all refunds
    - GET /api/admin/refunds/{id}/ - Refund details
    """

    permission_classes = [IsAdminUser]
    queryset = Refund.objects.all().select_related(
        'booking', 'payment'
    )
    serializer_class = AdminRefundSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'amount', 'status']
    ordering = ['-created_at']
    lookup_field = 'id'
