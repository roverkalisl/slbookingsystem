"""
Views for booking management with double-booking prevention.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from datetime import date, datetime
from decimal import Decimal

from .models import Booking, Availability
from .serializers import (
    BookingListSerializer, BookingDetailSerializer, BookingCreateSerializer,
    BookingCancelSerializer, PriceCalculationSerializer, PriceBreakdownSerializer,
    AvailabilityCheckSerializer, AvailabilityResponseSerializer
)
from .service import BookingService, BookingConflictError
from apps.properties.models import RoomType
from apps.properties.pricing import PricingCalculator


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for bookings with double-booking prevention.

    Endpoints:
    - POST /api/bookings/ - Create booking (CRITICAL: Transaction-safe)
    - GET /api/bookings/ - List my bookings
    - GET /api/bookings/{id}/ - Booking details
    - POST /api/bookings/{id}/cancel/ - Cancel booking
    - POST /api/bookings/{id}/confirm-payment/ - Confirm payment
    - POST /api/bookings/calculate-price/ - Calculate price
    - POST /api/bookings/check-availability/ - Check availability
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get bookings for current user"""
        user = self.request.user

        if user.is_staff:
            # Admin sees all bookings
            return Booking.objects.all().select_related('property', 'room_type', 'guest')

        # Guests see only their own bookings
        # Owners see bookings for their properties
        if user.has_role('property_owner'):
            return Booking.objects.filter(
                property__owner=user
            ) | Booking.objects.filter(
                guest=user
            )
        else:
            return Booking.objects.filter(guest=user)

    def get_serializer_class(self):
        """Choose serializer based on action"""
        if self.action == 'create':
            return BookingCreateSerializer
        elif self.action == 'list':
            return BookingListSerializer
        elif self.action == 'retrieve':
            return BookingDetailSerializer
        elif self.action == 'cancel':
            return BookingCancelSerializer
        elif self.action == 'calculate_price':
            return PriceCalculationSerializer
        elif self.action == 'check_availability':
            return AvailabilityCheckSerializer
        return BookingDetailSerializer

    def create(self, request, *args, **kwargs):
        """
        Create a booking (TRANSACTION-SAFE).

        CRITICAL: This uses database-level locking to prevent double bookings.

        POST /api/bookings/
        {
            "room_type_id": "uuid",
            "check_in_date": "2026-09-15",
            "check_out_date": "2026-09-17",
            "number_of_adults": 2,
            "number_of_children": 0,
            "number_of_rooms": 1,
            "guests": [
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john@example.com",
                    "phone": "123456789",
                    "is_primary_guest": true
                }
            ],
            "special_requests": "Late check-in",
            "discount_percent": "0",
            "discount_fixed": "0"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Get room type
            room_type = RoomType.objects.get(id=serializer.validated_data['room_type_id'])

            # Create booking (with transaction-safe locking)
            booking = BookingService.create_booking(
                room_type=room_type,
                guest=request.user,
                check_in=serializer.validated_data['check_in_date'],
                check_out=serializer.validated_data['check_out_date'],
                num_adults=serializer.validated_data['number_of_adults'],
                num_children=serializer.validated_data['number_of_children'],
                num_rooms=serializer.validated_data['number_of_rooms'],
                guest_details=serializer.validated_data.get('guests'),
                special_requests=serializer.validated_data.get('special_requests', ''),
                discount_percent=Decimal(str(serializer.validated_data.get('discount_percent', 0))),
                discount_fixed=Decimal(str(serializer.validated_data.get('discount_fixed', 0)))
            )

            # Return booking details
            output_serializer = BookingDetailSerializer(booking)

            return Response(
                {
                    'success': True,
                    'message': 'Booking created successfully',
                    'data': output_serializer.data
                },
                status=status.HTTP_201_CREATED
            )

        except BookingConflictError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'error_code': 'BOOKING_CONFLICT'
                },
                status=status.HTTP_409_CONFLICT
            )

        except ValueError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': f'Booking creation failed: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """Get booking details with permission check"""
        try:
            booking = BookingService.get_booking_details(pk, user=request.user)
            serializer = BookingDetailSerializer(booking)
            return Response(
                {
                    'success': True,
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except PermissionError as e:
            raise PermissionDenied(str(e))
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a booking.

        POST /api/bookings/{id}/cancel/
        {
            "reason": "Change of plans"
        }
        """
        try:
            booking = Booking.objects.get(id=pk)

            # Permission check
            if booking.guest != request.user and not request.user.is_staff:
                raise PermissionDenied("You can only cancel your own bookings")

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            reason = serializer.validated_data.get('reason', 'guest_request')

            # Cancel booking
            result = BookingService.cancel_booking(booking, reason=reason)

            return Response(
                {
                    'success': True,
                    'message': 'Booking cancelled successfully',
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
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """
        Confirm payment for a booking.

        POST /api/bookings/{id}/confirm-payment/
        {
            "transaction_reference": "TXN-123456"
        }
        """
        try:
            booking = Booking.objects.get(id=pk)

            # Permission check (only owner or staff can confirm payment)
            if booking.property.owner != request.user and not request.user.is_staff:
                raise PermissionDenied("Only property owner or admin can confirm payment")

            transaction_reference = request.data.get('transaction_reference')

            # Confirm payment
            booking = BookingService.confirm_payment(booking, transaction_reference)

            serializer = BookingDetailSerializer(booking)

            return Response(
                {
                    'success': True,
                    'message': 'Payment confirmed',
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )

        except Booking.DoesNotExist:
            return Response(
                {'error': 'Booking not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def calculate_price(self, request):
        """
        Calculate price for a booking without creating it.

        POST /api/bookings/calculate-price/
        {
            "room_type_id": "uuid",
            "check_in_date": "2026-09-15",
            "check_out_date": "2026-09-17",
            "number_of_adults": 2,
            "number_of_children": 0,
            "discount_percent": "0",
            "discount_fixed": "0"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            room_type = RoomType.objects.get(id=serializer.validated_data['room_type_id'])

            calculator = PricingCalculator(room_type)
            price_breakdown = calculator.calculate_booking_price(
                serializer.validated_data['check_in_date'],
                serializer.validated_data['check_out_date'],
                num_adults=serializer.validated_data['number_of_adults'],
                num_children=serializer.validated_data['number_of_children'],
                discount_percent=Decimal(str(serializer.validated_data.get('discount_percent', 0))),
                discount_fixed=Decimal(str(serializer.validated_data.get('discount_fixed', 0)))
            )

            price_serializer = PriceBreakdownSerializer(price_breakdown)

            return Response(
                {
                    'success': True,
                    'data': price_serializer.data
                },
                status=status.HTTP_200_OK
            )

        except RoomType.DoesNotExist:
            return Response(
                {'error': 'Room type not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def check_availability(self, request):
        """
        Check if a room is available for date range (non-blocking check).

        NOTE: This is for INFORMATIONAL purposes only.
        Always call create_booking to actually book (it has final check).

        POST /api/bookings/check-availability/
        {
            "room_type_id": "uuid",
            "check_in_date": "2026-09-15",
            "check_out_date": "2026-09-17"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            room_type = RoomType.objects.get(id=serializer.validated_data['room_type_id'])

            is_available, available_count = BookingService.check_availability(
                room_type,
                serializer.validated_data['check_in_date'],
                serializer.validated_data['check_out_date']
            )

            response_data = {
                'room_type_id': room_type.id,
                'is_available': is_available,
                'available_count': available_count,
                'total_rooms': room_type.total_rooms,
                'check_in_date': serializer.validated_data['check_in_date'],
                'check_out_date': serializer.validated_data['check_out_date']
            }

            response_serializer = AvailabilityResponseSerializer(response_data)

            return Response(
                {
                    'success': True,
                    'data': response_serializer.data
                },
                status=status.HTTP_200_OK
            )

        except RoomType.DoesNotExist:
            return Response(
                {'error': 'Room type not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
