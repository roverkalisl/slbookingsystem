"""
Booking models - CRITICAL for double-booking prevention.
"""

import uuid
from django.db import models
from apps.core.models import User
from apps.properties.models import Property, RoomType


class Booking(models.Model):
    """Core booking model with transaction safety"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('payment_pending', 'Payment Pending'),
        ('paid', 'Paid'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
        ('no_show', 'No Show'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_reference = models.CharField(max_length=50, unique=True, db_index=True)

    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE)
    guest = models.ForeignKey(User, on_delete=models.CASCADE)

    # Dates
    check_in_date = models.DateField(db_index=True)
    check_out_date = models.DateField(db_index=True)
    number_of_nights = models.IntegerField()

    # Guests
    number_of_adults = models.IntegerField()
    number_of_children = models.IntegerField(default=0)
    number_of_rooms = models.IntegerField(default=1)

    # Pricing
    room_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    service_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    # Special requests
    special_requests = models.TextField(blank=True, null=True)

    # Status
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending', db_index=True)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES, default='pending', db_index=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings'
        indexes = [
            models.Index(fields=['booking_reference']),
            models.Index(fields=['guest_id']),
            models.Index(fields=['property_id']),
            models.Index(fields=['room_type_id']),
            models.Index(fields=['check_in_date']),
            models.Index(fields=['check_out_date']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(check_in_date__lt=models.F('check_out_date')),
                name='check_in_before_checkout'
            )
        ]

    def __str__(self):
        return f"Booking {self.booking_reference}"


class BookingGuest(models.Model):
    """Guest information for a booking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='guests')

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)

    is_primary_guest = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking_guests'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Availability(models.Model):
    """Daily availability for rooms"""
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('booked', 'Booked'),
        ('blocked', 'Blocked'),
        ('maintenance', 'Maintenance'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE)

    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    available_count = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'availability'
        unique_together = ('room_type', 'date')
        indexes = [
            models.Index(fields=['room_type_id', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.room_type.name} - {self.date}"
