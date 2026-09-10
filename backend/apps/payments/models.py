"""Payment models"""

import uuid
from django.db import models
from apps.bookings.models import Booking

class Payment(models.Model):
    """Payment records"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending', db_index=True)

    payment_method = models.CharField(max_length=50)
    transaction_reference = models.CharField(max_length=255, blank=True, null=True, unique=True, db_index=True)

    gateway_name = models.CharField(max_length=100, blank=True, null=True)
    gateway_response = models.JSONField(blank=True, null=True)

    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['booking_id']),
            models.Index(fields=['status']),
            models.Index(fields=['transaction_reference']),
        ]

    def __str__(self):
        return f"Payment for {self.booking.booking_reference}"


class Refund(models.Model):
    """Refund records"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending', db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'refunds'
        indexes = [
            models.Index(fields=['booking_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Refund for {self.booking.booking_reference}"
