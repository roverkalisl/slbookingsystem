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


class WhatsAppNotification(models.Model):
    """WhatsApp notification events and logs"""
    EVENT_CHOICES = [
        ('new_booking', 'New Booking'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('booking_modified', 'Booking Modified'),
        ('payment_received', 'Payment Received'),
        ('check_in_reminder', 'Check-in Reminder'),
        ('check_out_reminder', 'Check-out Reminder'),
        ('new_enquiry', 'New Enquiry'),
        ('property_approved', 'Property Approved'),
        ('property_rejected', 'Property Rejected'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('read', 'Read'),
        ('not_configured', 'WhatsApp Not Configured'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient_phone = models.CharField(max_length=20, db_index=True)

    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES, db_index=True)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, blank=True, null=True)
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, blank=True, null=True)

    message_text = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending', db_index=True)

    whatsapp_message_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'whatsapp_notifications'
        indexes = [
            models.Index(fields=['recipient_phone']),
            models.Index(fields=['event_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"WhatsApp: {self.event_type} to {self.recipient_phone} ({self.status})"
