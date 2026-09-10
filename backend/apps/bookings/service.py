"""
Booking service with transaction-safe operations and double-booking prevention.

CRITICAL: This service implements database-level locking to prevent double bookings.
All booking operations use SELECT FOR UPDATE and atomic transactions.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple
from django.db import transaction
from django.utils.timezone import now
import uuid
import random
import string

from .models import Booking, BookingGuest, Availability
from apps.properties.models import RoomType, Property
from apps.core.models import User
from apps.properties.pricing import PricingCalculator


class BookingService:
    """Service for creating and managing bookings with double-booking protection"""

    @staticmethod
    def generate_booking_reference() -> str:
        """Generate unique booking reference in format SLB-YYYY-XXXXXX"""
        year = datetime.now().year
        random_suffix = ''.join(random.choices(string.digits, k=6))
        return f"SLB-{year}-{random_suffix}"

    @staticmethod
    def check_availability(
        room_type: RoomType,
        check_in: date,
        check_out: date,
        exclude_booking_id: str = None
    ) -> Tuple[bool, int]:
        """
        Check if room is available for date range (non-blocking check).

        This is a READ-ONLY check and should NOT be used for booking creation.
        It's for informational purposes only.

        Returns: (is_available, available_count)
        """
        # Get confirmed/paid bookings that overlap with requested dates
        overlapping_bookings = Booking.objects.filter(
            room_type=room_type,
            status__in=['confirmed', 'paid', 'completed'],
            check_in_date__lt=check_out,
            check_out_date__gt=check_in
        )

        # Exclude current booking if doing update
        if exclude_booking_id:
            overlapping_bookings = overlapping_bookings.exclude(id=exclude_booking_id)

        booked_count = overlapping_bookings.count()
        available_count = room_type.total_rooms - booked_count

        return available_count > 0, available_count

    @staticmethod
    @transaction.atomic
    def create_booking(
        room_type: RoomType,
        guest: User,
        check_in: date,
        check_out: date,
        num_adults: int = 1,
        num_children: int = 0,
        num_rooms: int = 1,
        guest_details: List[Dict] = None,
        special_requests: str = None,
        discount_percent: Decimal = Decimal('0'),
        discount_fixed: Decimal = Decimal('0')
    ) -> Booking:
        """
        Create a booking with DOUBLE-BOOKING PREVENTION.

        CRITICAL: This method uses database-level locking to ensure atomicity.
        It uses SELECT FOR UPDATE to lock the room_type row during the transaction.

        Args:
            room_type: The room type being booked
            guest: The guest user
            check_in: Check-in date (inclusive)
            check_out: Check-out date (exclusive - guest leaves this day)
            num_adults: Number of adults
            num_children: Number of children
            num_rooms: Number of rooms to book
            guest_details: List of guest info dicts [{first_name, last_name, email, phone}]
            special_requests: Special requests from guest
            discount_percent: Discount percentage to apply
            discount_fixed: Fixed discount amount to apply

        Returns:
            Booking object (status='pending', payment_status='pending')

        Raises:
            ValueError: If dates invalid or room not available
            BookingConflictError: If room not available for date range
        """

        # Validate dates
        if check_in >= check_out:
            raise ValueError("Check-out date must be after check-in date")

        num_nights = (check_out - check_in).days
        if num_nights <= 0:
            raise ValueError("Booking must be at least 1 night")

        # Lock room_type row for duration of this transaction
        # This prevents concurrent bookings from reading stale data
        room_type_locked = RoomType.objects.select_for_update().get(id=room_type.id)

        # ========== CRITICAL SECTION: Double-Booking Prevention ==========
        # Check for overlapping confirmed/paid bookings INSIDE the transaction
        # After SELECT FOR UPDATE, no other transaction can modify this row
        overlapping_bookings = Booking.objects.filter(
            room_type=room_type_locked,
            status__in=['confirmed', 'paid', 'completed'],
            check_in_date__lt=check_out,
            check_out_date__gt=check_in
        ).count()

        # Check if we have enough available rooms
        if overlapping_bookings + num_rooms > room_type_locked.total_rooms:
            raise BookingConflictError(
                f"Room not available for selected dates. "
                f"Only {room_type_locked.total_rooms - overlapping_bookings} "
                f"room(s) available, but {num_rooms} requested."
            )
        # ========== END CRITICAL SECTION ==========

        # Calculate pricing
        calculator = PricingCalculator(room_type_locked)
        price_breakdown = calculator.calculate_booking_price(
            check_in, check_out,
            num_adults=num_adults,
            num_children=num_children,
            discount_percent=discount_percent,
            discount_fixed=discount_fixed
        )

        # Create booking
        booking = Booking.objects.create(
            id=uuid.uuid4(),
            booking_reference=BookingService.generate_booking_reference(),
            property=room_type_locked.property,
            room_type=room_type_locked,
            guest=guest,
            check_in_date=check_in,
            check_out_date=check_out,
            number_of_nights=num_nights,
            number_of_adults=num_adults,
            number_of_children=num_children,
            number_of_rooms=num_rooms,
            room_price=price_breakdown['room_price_per_night'],
            subtotal=price_breakdown['subtotal'],
            discount=price_breakdown['discount'],
            service_fee=price_breakdown['service_fee'],
            tax=price_breakdown['tax'],
            total_price=price_breakdown['total'],
            special_requests=special_requests,
            status='pending',
            payment_status='pending'
        )

        # Add guest details if provided
        if guest_details:
            guest_objects = []
            for idx, guest_info in enumerate(guest_details):
                is_primary = idx == 0 or guest_info.get('is_primary_guest', False)
                guest_objects.append(
                    BookingGuest(
                        booking=booking,
                        first_name=guest_info.get('first_name', ''),
                        last_name=guest_info.get('last_name', ''),
                        email=guest_info.get('email', ''),
                        phone=guest_info.get('phone', ''),
                        is_primary_guest=is_primary
                    )
                )
            BookingGuest.objects.bulk_create(guest_objects)
        else:
            # Create primary guest from user info
            BookingGuest.objects.create(
                booking=booking,
                first_name=guest.first_name or 'Guest',
                last_name=guest.last_name or '',
                email=guest.email,
                phone='',
                is_primary_guest=True
            )

        # Update availability (mark dates as booked)
        BookingService._update_availability(room_type_locked, check_in, check_out, 'booked')

        return booking

    @staticmethod
    @transaction.atomic
    def cancel_booking(booking: Booking, reason: str = 'guest_request') -> Dict:
        """
        Cancel a booking and calculate refund.

        Args:
            booking: Booking to cancel
            reason: Reason for cancellation

        Returns:
            Dict with cancellation details and refund info
        """
        if booking.status == 'cancelled':
            raise ValueError("Booking is already cancelled")

        if booking.status not in ['pending', 'confirmed', 'payment_pending', 'paid']:
            raise ValueError(f"Cannot cancel booking with status: {booking.status}")

        # Lock booking for update
        booking = Booking.objects.select_for_update().get(id=booking.id)

        # Determine refund amount based on cancellation policy
        property_obj = booking.property
        days_until_checkin = (booking.check_in_date - date.today()).days

        # Default cancellation policy (can be customized per property)
        full_refund_days = 7  # 7+ days before = full refund
        partial_refund_days = 3  # 3+ days before = partial refund
        partial_refund_percent = Decimal('50')  # 50% refund

        if days_until_checkin >= full_refund_days:
            refund_percent = Decimal('100')
        elif days_until_checkin >= partial_refund_days:
            refund_percent = partial_refund_percent
        else:
            refund_percent = Decimal('0')

        refund_amount = booking.total_price * (refund_percent / Decimal('100'))

        # Update booking status
        booking.status = 'cancelled'
        booking.save()

        # Release availability
        BookingService._update_availability(
            booking.room_type,
            booking.check_in_date,
            booking.check_out_date,
            'available'
        )

        return {
            'booking_id': booking.id,
            'booking_reference': booking.booking_reference,
            'refund_amount': refund_amount,
            'refund_percent': refund_percent,
            'cancellation_reason': reason,
            'status': 'cancelled'
        }

    @staticmethod
    def _update_availability(room_type: RoomType, check_in: date, check_out: date, status: str):
        """
        Update availability records for date range.

        Args:
            room_type: Room type to update
            check_in: Start date (inclusive)
            check_out: End date (exclusive)
            status: 'booked' or 'available'
        """
        current_date = check_in
        while current_date < check_out:
            availability, created = Availability.objects.get_or_create(
                room_type=room_type,
                date=current_date,
                defaults={'available_count': room_type.total_rooms}
            )

            if status == 'booked':
                availability.available_count -= 1
            elif status == 'available':
                availability.available_count += 1

            availability.status = status
            availability.save()

            current_date += timedelta(days=1)

    @staticmethod
    @transaction.atomic
    def confirm_payment(booking: Booking, transaction_reference: str = None) -> Booking:
        """
        Confirm payment for a booking.

        Args:
            booking: Booking to confirm
            transaction_reference: Payment transaction reference

        Returns:
            Updated booking object
        """
        booking = Booking.objects.select_for_update().get(id=booking.id)

        booking.status = 'confirmed'
        booking.payment_status = 'paid'
        booking.save()

        # TODO: Send confirmation email to guest

        return booking

    @staticmethod
    def get_booking_details(booking_id: str, user: User = None) -> Booking:
        """
        Get booking details with permission check.

        Args:
            booking_id: Booking ID
            user: User requesting the booking (for permission check)

        Returns:
            Booking object

        Raises:
            PermissionError: If user doesn't have access
        """
        try:
            booking = Booking.objects.select_related(
                'property', 'room_type', 'guest'
            ).prefetch_related('guests').get(id=booking_id)

            # Permission check: only guest, owner, or admin can view
            if user and not user.is_staff:
                if booking.guest != user and booking.property.owner != user:
                    raise PermissionError("You don't have access to this booking")

            return booking

        except Booking.DoesNotExist:
            raise ValueError("Booking not found")


class BookingConflictError(Exception):
    """Exception raised when a booking cannot be created due to conflict"""
    pass
