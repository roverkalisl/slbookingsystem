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
    ).prefetch_related('guests', 'payments', 'refunds')
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
            booking.status = 'cancelled'
            booking.save()

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

        # Check if payment can be refunded
        if payment.status not in ['paid', 'partially_refunded']:
            return Response(
                {'error': f'Cannot refund payment with status: {payment.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        amount = serializer.validated_data.get('amount', payment.amount)
        reason = serializer.validated_data.get('reason', 'Admin refund')

        # Validate refund amount
        if amount > payment.amount:
            return Response(
                {'error': f'Refund amount ({amount}) exceeds payment amount ({payment.amount})'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create refund record
        with transaction.atomic():
            refund = Refund.objects.create(
                booking=payment.booking,
                payment=payment,
                amount=amount,
                reason=reason,
                status='pending'
            )

            # Update payment status if full refund
            if amount >= payment.amount:
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
