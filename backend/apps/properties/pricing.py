"""
Pricing service for calculating room rates based on dates and rules.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple
from django.db.models import Q

from .models import RoomType, Pricing, SeasonalRate


class PricingCalculator:
    """Calculate pricing for bookings based on room rates, dates, and rules"""

    def __init__(self, room_type: RoomType):
        self.room_type = room_type
        self.pricing = self._get_pricing()

    def _get_pricing(self) -> Pricing:
        """Get pricing configuration for room type"""
        try:
            return Pricing.objects.get(room_type=self.room_type)
        except Pricing.DoesNotExist:
            # Create default pricing if not exists
            return Pricing.objects.create(
                room_type=self.room_type,
                base_price=Decimal('0.00')
            )

    def get_nightly_rate(self, check_date: date) -> Decimal:
        """
        Get the rate for a specific date.

        Priority:
        1. Seasonal rate (if date falls within seasonal range)
        2. Weekend rate (Friday-Sunday)
        3. Base price
        """

        # Check seasonal rates first (highest priority)
        seasonal = SeasonalRate.objects.filter(
            room_type=self.room_type,
            start_date__lte=check_date,
            end_date__gte=check_date
        ).first()

        if seasonal:
            return seasonal.price_per_night

        # Check weekend rate (Friday=4, Saturday=5, Sunday=6)
        if check_date.weekday() >= 4:
            if self.pricing.weekend_price:
                return self.pricing.weekend_price

        # Fall back to base price
        return self.pricing.base_price

    def get_date_range_rates(self, check_in: date, check_out: date) -> List[Tuple[date, Decimal]]:
        """
        Get rates for each date in the range.

        Returns: List of (date, rate) tuples
        """

        rates = []
        current_date = check_in

        while current_date < check_out:
            rate = self.get_nightly_rate(current_date)
            rates.append((current_date, rate))
            current_date += timedelta(days=1)

        return rates

    def calculate_booking_price(
        self,
        check_in: date,
        check_out: date,
        num_adults: int = 1,
        num_children: int = 0,
        discount_percent: Decimal = Decimal('0'),
        discount_fixed: Decimal = Decimal('0'),
        num_rooms: int = 1
    ) -> Dict[str, Decimal]:
        """
        Calculate total booking price with all fees and taxes.

        num_rooms identical rooms are charged for every night. The per-date
        rates (and room_price_per_night) stay per single room; only the room
        subtotal is multiplied, so fees/taxes derived from it scale once.

        Returns: Dictionary with price breakdown
        """

        # 1. Calculate number of nights
        num_nights = (check_out - check_in).days
        if num_nights <= 0:
            raise ValueError("Check-out date must be after check-in date")
        if num_rooms < 1:
            raise ValueError("At least 1 room must be booked")

        # 2. Get nightly rates for each date
        date_rates = self.get_date_range_rates(check_in, check_out)

        # 3. Calculate room subtotal (per-room nightly rates x number of rooms)
        room_subtotal = sum(rate for _, rate in date_rates) * num_rooms

        # 4. Add guest fees
        guest_fees = Decimal('0')

        # Extra adult fee
        included_adults = 2 * num_rooms  # Default 2 adults included per room in base price
        if num_adults > included_adults:
            extra_adults = num_adults - included_adults
            if self.pricing.extra_guest_fee:
                guest_fees += extra_adults * self.pricing.extra_guest_fee * num_nights

        # Child fee
        if num_children > 0 and self.pricing.child_fee:
            guest_fees += num_children * self.pricing.child_fee * num_nights

        # 5. Calculate subtotal before discounts and fees
        subtotal = room_subtotal + guest_fees

        # 6. Apply discounts
        discount = Decimal('0')

        if discount_percent > 0:
            discount = subtotal * (discount_percent / Decimal('100'))

        if discount_fixed > 0:
            discount += discount_fixed

        # Ensure discount doesn't exceed subtotal
        discount = min(discount, subtotal)

        discounted_subtotal = subtotal - discount

        # 7. Calculate service fee (on discounted subtotal)
        service_fee = discounted_subtotal * (self.pricing.service_fee_percent / Decimal('100'))

        # 8. Calculate tax (on subtotal + service fee)
        taxable_amount = discounted_subtotal + service_fee
        tax = taxable_amount * (self.pricing.tax_percent / Decimal('100'))

        # 9. Calculate total
        total = discounted_subtotal + service_fee + tax

        return {
            'nights': num_nights,
            'num_rooms': num_rooms,
            'room_price_per_night': date_rates[0][1] if date_rates else Decimal('0'),
            'room_subtotal': room_subtotal,
            'guest_fees': guest_fees,
            'subtotal': subtotal,
            'discount': discount,
            'service_fee': service_fee,
            'tax': tax,
            'total': total,
            'currency': self.pricing.currency,
            'date_breakdown': [
                {'date': date_obj.isoformat(), 'rate': str(rate)}
                for date_obj, rate in date_rates
            ]
        }

    @staticmethod
    def create_default_pricing(room_type: RoomType, base_price: Decimal):
        """Create default pricing for a room type"""
        return Pricing.objects.create(
            room_type=room_type,
            base_price=base_price,
            service_fee_percent=Decimal('5.0'),  # 5% service fee
            tax_percent=Decimal('10.0'),  # 10% tax
            currency='LKR'
        )


# Models to be created - Add to properties/models.py

PRICING_MODELS_TO_ADD = """

class Pricing(models.Model):
    \"\"\"Base pricing for room types\"\"\"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_type = models.OneToOneField(RoomType, on_delete=models.CASCADE, unique=True)

    base_price = models.DecimalField(max_digits=12, decimal_places=2)
    weekend_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    extra_guest_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    child_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    service_fee_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)

    currency = models.CharField(max_length=3, default='LKR')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pricing'
        indexes = [
            models.Index(fields=['room_type_id']),
        ]

    def __str__(self):
        return f"Pricing for {self.room_type.name}: {self.base_price} {self.currency}/night"


class SeasonalRate(models.Model):
    \"\"\"Seasonal pricing overrides base pricing\"\"\"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='seasonal_rates')

    name = models.CharField(max_length=100)  # "High Season", "Off Season", etc.
    price_per_night = models.DecimalField(max_digits=12, decimal_places=2)

    start_date = models.DateField()
    end_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'seasonal_rates'
        indexes = [
            models.Index(fields=['room_type_id']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"
"""
