"""Notification models"""

import uuid
from django.db import models
from apps.core.models import User
from apps.bookings.models import Booking
from apps.properties.models import Property


class Notification(models.Model):
    """Notification log"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ]

    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('in_app', 'In-App'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)

    notification_type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    message = models.TextField()

    related_booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, blank=True, null=True)
    related_property = models.ForeignKey(Property, on_delete=models.SET_NULL, blank=True, null=True)

    channel = models.CharField(max_length=50, choices=CHANNEL_CHOICES, default='email')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending', db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        indexes = [
            models.Index(fields=['recipient_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Notification to {self.recipient.email}: {self.title}"
