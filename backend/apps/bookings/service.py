"""
Booking service with transaction-safe operations and double-booking prevention.

CRITICAL: This service implements database-level locking to prevent double bookings.
All booking operations use SELECT FOR UPDATE and atomic transactions.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Sum
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

    # Statuses in which a booking still holds its rooms and may be paid/confirmed.
    PAYABLE_STATUSES = ('pending', 'payment_pending', 'confirmed')

    @staticmethod
    def generate_booking_reference() -> str:
        """Generate unique booking reference in format SLB-YYYY-XXXXXX"""
        year = datetime.now().year
        random_suffix = ''.join(random.choices(string.digits, k=6))
        return f"SLB-{year}-{random_suffix}"

    @staticmethod
    def _rooms_held(bookings) -> int:
        """
        Total room inventory held by a queryset of bookings.

        A single booking can hold several identical rooms (number_of_rooms),
        so inventory must be the SUM of number_of_rooms - counting booking
        rows would let a 3-room booking consume only 1 slot.
        """
        return bookings.aggregate(total=Sum('number_of_rooms'))['total'] or 0

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
        # Get bookings that still hold inventory and overlap with requested
        # dates. Must include 'pending' — see the comment in create_booking's
        # critical section for why pending bookings occupy a room slot too.
        overlapping_bookings = Booking.objects.filter(
            room_type=room_type,
            status__in=['pending', 'confirmed', 'payment_pending', 'paid', 'completed'],
            check_in_date__lt=check_out,
            check_out_date__gt=check_in
        )

        # Exclude current booking if doing update
        if exclude_booking_id:
            overlapping_bookings = overlapping_bookings.exclude(id=exclude_booking_id)

        booked_count = BookingService._rooms_held(overlapping_bookings)
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
            discount_percent: Discount percentage to apply (system-controlled only -
                never pass client/guest input; the booking API passes none)
            discount_fixed: Fixed discount amount to apply (system-controlled only)

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

        if check_in < date.today():
            raise ValueError("Check-in date cannot be in the past")

        if num_rooms < 1:
            raise ValueError("At least 1 room must be booked")

        # Property and room must both be active/approved - a guest should
        # never be able to book a draft, pending, rejected, suspended or
        # unpublished property, or a room the owner has deactivated.
        if room_type.property.status != 'approved':
            raise BookingConflictError("This property is not currently accepting bookings.")

        if not room_type.is_active:
            raise BookingConflictError("This room type is not currently available for booking.")

        # Validate occupancy against the combined capacity of every booked room:
        # each room's max_adults / max_children / total_occupancy limit applies
        # per room, so N identical rooms hold N times as many guests.
        total_guests = num_adults + num_children
        max_adults = room_type.max_adults * num_rooms
        max_children = room_type.max_children * num_rooms
        max_occupancy = room_type.total_occupancy * num_rooms
        rooms_label = "This room allows" if num_rooms == 1 else f"{num_rooms} rooms of this type allow"
        if num_adults > max_adults:
            raise ValueError(
                f"{rooms_label} a maximum of {max_adults} adult(s), but {num_adults} were requested."
            )
        if num_children > max_children:
            raise ValueError(
                f"{rooms_label} a maximum of {max_children} child(ren), but {num_children} were requested."
            )
        if total_guests > max_occupancy:
            raise ValueError(
                f"{rooms_label} a maximum occupancy of {max_occupancy} guest(s), "
                f"but {total_guests} were requested."
            )

        # Lock room_type row for duration of this transaction
        # This prevents concurrent bookings from reading stale data
        room_type_locked = RoomType.objects.select_for_update().get(id=room_type.id)

        # Owner-blocked or maintenance dates take priority over inventory
        # count - even if rooms are numerically available, a blocked date
        # means the owner has taken it off the market.
        if Availability.objects.filter(
            room_type=room_type_locked,
            date__gte=check_in,
            date__lt=check_out,
            status__in=['blocked', 'maintenance']
        ).exists():
            raise BookingConflictError("The selected room is not available for these dates.")

        # ========== CRITICAL SECTION: Double-Booking Prevention ==========
        # Count overlapping bookings that still hold inventory INSIDE the
        # transaction. This MUST include 'pending' bookings: a booking stays
        # pending until the owner explicitly confirms or rejects it (no
        # payment gateway gates this), so pending requests already occupy a
        # room slot and must count against total_rooms just like confirmed
        # ones — otherwise unlimited overlapping pending bookings could be
        # created past capacity. Only cancelled/rejected bookings release
        # their slot (handled via _update_availability + this status list).
        # After SELECT FOR UPDATE, no other transaction can modify this row.
        # Inventory is the SUM of number_of_rooms, not the booking row count.
        rooms_held = BookingService._rooms_held(Booking.objects.filter(
            room_type=room_type_locked,
            status__in=['pending', 'confirmed', 'payment_pending', 'paid', 'completed'],
            check_in_date__lt=check_out,
            check_out_date__gt=check_in
        ))

        # Check if we have enough available rooms
        if rooms_held + num_rooms > room_type_locked.total_rooms:
            raise BookingConflictError(
                f"Room not available for selected dates. "
                f"Only {max(room_type_locked.total_rooms - rooms_held, 0)} "
                f"room(s) available, but {num_rooms} requested."
            )
        # ========== END CRITICAL SECTION ==========

        # Calculate pricing
        calculator = PricingCalculator(room_type_locked)
        price_breakdown = calculator.calculate_booking_price(
            check_in, check_out,
            num_adults=num_adults,
            num_children=num_children,
            num_rooms=num_rooms,
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
        BookingService._update_availability(room_type_locked, check_in, check_out, 'booked', num_rooms)

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
        # Lock booking for update first, so the status checks below see the
        # current row and a concurrent cancel can't release its rooms twice
        booking = Booking.objects.select_for_update().get(id=booking.id)

        if booking.status == 'cancelled':
            raise ValueError("Booking is already cancelled")

        if booking.status not in ['pending', 'confirmed', 'payment_pending', 'paid']:
            raise ValueError(f"Cannot cancel booking with status: {booking.status}")

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
            'available',
            booking.number_of_rooms
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
    def _update_availability(room_type: RoomType, check_in: date, check_out: date, status: str, quantity: int = 1):
        """
        Update availability records for date range.

        Args:
            room_type: Room type to update
            check_in: Start date (inclusive)
            check_out: End date (exclusive)
            status: 'booked' or 'available'
            quantity: Number of rooms being booked or released (booking.number_of_rooms)
        """
        current_date = check_in
        while current_date < check_out:
            availability, created = Availability.objects.get_or_create(
                room_type=room_type,
                date=current_date,
                defaults={'available_count': room_type.total_rooms}
            )

            if status == 'booked':
                availability.available_count -= quantity
            elif status == 'available':
                availability.available_count += quantity

            # Releasing a booking must never undo an owner's block/maintenance
            # on that date - only the owner's unblock action may do that.
            if availability.status not in ('blocked', 'maintenance'):
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

        # Only bookings that still hold their rooms can be paid/confirmed.
        # Confirming a cancelled/rejected booking would silently re-occupy
        # inventory that may already have been sold to someone else.
        if booking.status not in BookingService.PAYABLE_STATUSES:
            raise ValueError(f"Cannot confirm payment for booking with status: {booking.status}")

        booking.status = 'confirmed'
        booking.payment_status = 'paid'
        booking.save()

        return booking

    @staticmethod
    @transaction.atomic
    def owner_confirm_booking(booking: Booking) -> Booking:
        """
        Owner confirms a pending booking request (no payment gateway required).

        Args:
            booking: Booking to confirm

        Returns:
            Updated booking object

        Raises:
            ValueError: If booking is not in a confirmable state
        """
        booking = Booking.objects.select_for_update().get(id=booking.id)

        if booking.status != 'pending':
            raise ValueError(f"Cannot confirm booking with status: {booking.status}")

        booking.status = 'confirmed'
        booking.save()

        return booking

    @staticmethod
    @transaction.atomic
    def owner_reject_booking(booking: Booking, reason: str = '') -> Booking:
        """
        Owner rejects a pending booking request and releases the held inventory.

        Args:
            booking: Booking to reject
            reason: Optional reason shown to the guest

        Returns:
            Updated booking object

        Raises:
            ValueError: If booking is not in a rejectable state
        """
        booking = Booking.objects.select_for_update().get(id=booking.id)

        if booking.status != 'pending':
            raise ValueError(f"Cannot reject booking with status: {booking.status}")

        booking.status = 'rejected'
        booking.save()

        BookingService._update_availability(
            booking.room_type,
            booking.check_in_date,
            booking.check_out_date,
            'available',
            booking.number_of_rooms
        )

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

        except (Booking.DoesNotExist, DjangoValidationError):
            # Missing or malformed id - the view maps this to 404
            raise ValueError("Booking not found")


class BookingConflictError(Exception):
    """Exception raised when a booking cannot be created due to conflict"""
    pass
