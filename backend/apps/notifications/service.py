"""
Notification service with support for multiple channels.

Supports: Email, SMS, Push notifications, In-app messages
"""

from abc import ABC, abstractmethod
from typing import Dict, List
from django.core.mail import send_html_email
from django.template.loader import render_to_string
from django.urls import reverse

from .models import Notification
from apps.bookings.models import Booking


class NotificationChannel(ABC):
    """Abstract base class for notification channels"""

    @abstractmethod
    def send(self, recipient: str, subject: str, message: str, **kwargs) -> Dict:
        """
        Send a notification.

        Returns:
            {
                'success': bool,
                'message_id': str,
                'error': str (if applicable)
            }
        """
        pass


class EmailChannel(NotificationChannel):
    """Email notification channel"""

    def send(self, recipient: str, subject: str, message: str, **kwargs) -> Dict:
        """
        Send email notification.

        Args:
            recipient: Email address
            subject: Email subject
            message: Email body (HTML)
            **kwargs: Additional context

        Returns:
            Dict with send result
        """
        try:
            send_html_email(
                subject=subject,
                message=message,
                from_email='noreply@slbooking.hotel.lk',
                recipient_list=[recipient]
            )
            return {
                'success': True,
                'message_id': f"email_{recipient}_{subject}",
                'channel': 'email'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'channel': 'email'
            }


class SMSChannel(NotificationChannel):
    """SMS notification channel (placeholder for Twilio/AWS SNS)"""

    def send(self, recipient: str, subject: str, message: str, **kwargs) -> Dict:
        """
        Send SMS notification.

        In production, would integrate with Twilio or AWS SNS.
        """
        # Placeholder: In production, call Twilio or AWS SNS API
        return {
            'success': True,
            'message_id': f"sms_{recipient}",
            'channel': 'sms',
            'note': 'SMS integration not yet implemented'
        }


class PushNotificationChannel(NotificationChannel):
    """Push notification channel (placeholder for Firebase Cloud Messaging)"""

    def send(self, recipient: str, subject: str, message: str, **kwargs) -> Dict:
        """
        Send push notification.

        In production, would integrate with Firebase Cloud Messaging.
        """
        # Placeholder: In production, call Firebase API
        return {
            'success': True,
            'message_id': f"push_{recipient}",
            'channel': 'push',
            'note': 'Push notification integration not yet implemented'
        }


class InAppChannel(NotificationChannel):
    """In-app notification channel"""

    def send(self, recipient: str, subject: str, message: str, **kwargs) -> Dict:
        """
        Send in-app notification.

        Stores in database for display in app.
        """
        # In-app notifications are stored via NotificationService
        return {
            'success': True,
            'message_id': f"inapp_{recipient}",
            'channel': 'in_app'
        }


class NotificationService:
    """Service for sending notifications via multiple channels"""

    CHANNELS = {
        'email': EmailChannel,
        'sms': SMSChannel,
        'push': PushNotificationChannel,
        'in_app': InAppChannel,
    }

    TEMPLATES = {
        'booking_confirmation': 'emails/booking_confirmation.html',
        'booking_cancellation': 'emails/booking_cancellation.html',
        'payment_received': 'emails/payment_received.html',
        'review_request': 'emails/review_request.html',
        'password_reset': 'emails/password_reset.html',
    }

    @staticmethod
    def send_booking_confirmation(booking: Booking) -> Dict:
        """
        Send booking confirmation email to guest.

        Args:
            booking: Booking object

        Returns:
            Dict with send result
        """
        # Prepare context
        context = {
            'booking_reference': booking.booking_reference,
            'property_name': booking.property.name,
            'room_type_name': booking.room_type.name,
            'check_in': booking.check_in_date,
            'check_out': booking.check_out_date,
            'guests': booking.guests.all(),
            'total_price': booking.total_price,
            'guest_name': booking.guest.get_full_name() or booking.guest.email,
            'booking_url': f"https://slbooking.hotel.lk/bookings/{booking.id}/"
        }

        # Render template
        subject = f"Booking Confirmation - {booking.booking_reference}"
        html_message = render_to_string(
            NotificationService.TEMPLATES['booking_confirmation'],
            context
        )

        # Send email
        channel = EmailChannel()
        result = channel.send(
            recipient=booking.guest.email,
            subject=subject,
            message=html_message
        )

        # Create notification record
        notification = Notification.objects.create(
            recipient=booking.guest,
            notification_type='booking_confirmation',
            title=subject,
            message=f"Your booking {booking.booking_reference} is confirmed",
            related_booking=booking,
            channel='email',
            status='sent' if result['success'] else 'failed'
        )

        return {
            'success': result['success'],
            'notification_id': notification.id,
            'booking_reference': booking.booking_reference
        }

    @staticmethod
    def send_owner_notification(booking: Booking) -> Dict:
        """
        Send booking notification to property owner.

        Args:
            booking: Booking object

        Returns:
            Dict with send result
        """
        context = {
            'booking_reference': booking.booking_reference,
            'guest_name': booking.guest.get_full_name(),
            'guest_email': booking.guest.email,
            'check_in': booking.check_in_date,
            'check_out': booking.check_out_date,
            'rooms': booking.number_of_rooms,
            'adults': booking.number_of_adults,
            'children': booking.number_of_children,
            'total_price': booking.total_price
        }

        subject = f"New Booking - {booking.booking_reference}"
        html_message = render_to_string(
            'emails/new_booking_notification.html',
            context
        )

        channel = EmailChannel()
        result = channel.send(
            recipient=booking.property.owner.email,
            subject=subject,
            message=html_message
        )

        notification = Notification.objects.create(
            recipient=booking.property.owner,
            notification_type='new_booking',
            title=subject,
            message=f"New booking {booking.booking_reference}",
            related_booking=booking,
            channel='email',
            status='sent' if result['success'] else 'failed'
        )

        return {
            'success': result['success'],
            'notification_id': notification.id
        }

    @staticmethod
    def send_cancellation_notification(
        booking: Booking,
        refund_amount: float,
        refund_percent: float
    ) -> Dict:
        """
        Send booking cancellation notification.

        Args:
            booking: Booking object
            refund_amount: Amount refunded
            refund_percent: Refund percentage

        Returns:
            Dict with send result
        """
        context = {
            'booking_reference': booking.booking_reference,
            'guest_name': booking.guest.get_full_name(),
            'refund_amount': refund_amount,
            'refund_percent': refund_percent
        }

        subject = f"Booking Cancelled - {booking.booking_reference}"
        html_message = render_to_string(
            NotificationService.TEMPLATES['booking_cancellation'],
            context
        )

        channel = EmailChannel()
        result = channel.send(
            recipient=booking.guest.email,
            subject=subject,
            message=html_message
        )

        notification = Notification.objects.create(
            recipient=booking.guest,
            notification_type='booking_cancellation',
            title=subject,
            message=f"Your booking {booking.booking_reference} has been cancelled",
            related_booking=booking,
            channel='email',
            status='sent' if result['success'] else 'failed'
        )

        return {
            'success': result['success'],
            'notification_id': notification.id
        }

    @staticmethod
    def send_payment_confirmation(booking: Booking, amount: float) -> Dict:
        """
        Send payment confirmation email.

        Args:
            booking: Booking object
            amount: Payment amount

        Returns:
            Dict with send result
        """
        context = {
            'booking_reference': booking.booking_reference,
            'guest_name': booking.guest.get_full_name(),
            'amount': amount,
            'currency': 'LKR'
        }

        subject = f"Payment Received - {booking.booking_reference}"
        html_message = render_to_string(
            NotificationService.TEMPLATES['payment_received'],
            context
        )

        channel = EmailChannel()
        result = channel.send(
            recipient=booking.guest.email,
            subject=subject,
            message=html_message
        )

        notification = Notification.objects.create(
            recipient=booking.guest,
            notification_type='payment_received',
            title=subject,
            message=f"Payment of LKR {amount} received for booking {booking.booking_reference}",
            related_booking=booking,
            channel='email',
            status='sent' if result['success'] else 'failed'
        )

        return {
            'success': result['success'],
            'notification_id': notification.id
        }

    @staticmethod
    def send_review_request(booking: Booking) -> Dict:
        """
        Send review request email to guest (after stay completion).

        Args:
            booking: Completed booking object

        Returns:
            Dict with send result
        """
        context = {
            'booking_reference': booking.booking_reference,
            'guest_name': booking.guest.get_full_name(),
            'property_name': booking.property.name,
            'review_url': f"https://slbooking.hotel.lk/bookings/{booking.id}/review/"
        }

        subject = f"Please review your stay at {booking.property.name}"
        html_message = render_to_string(
            NotificationService.TEMPLATES['review_request'],
            context
        )

        channel = EmailChannel()
        result = channel.send(
            recipient=booking.guest.email,
            subject=subject,
            message=html_message
        )

        notification = Notification.objects.create(
            recipient=booking.guest,
            notification_type='review_request',
            title=subject,
            message=f"Please share your experience at {booking.property.name}",
            related_booking=booking,
            channel='email',
            status='sent' if result['success'] else 'failed'
        )

        return {
            'success': result['success'],
            'notification_id': notification.id
        }

    @staticmethod
    def send_multi_channel(
        recipient_email: str,
        subject: str,
        message: str,
        channels: List[str] = None
    ) -> Dict:
        """
        Send notification via multiple channels.

        Args:
            recipient_email: Email address
            subject: Message subject
            message: Message body
            channels: List of channels (default: ['email'])

        Returns:
            Dict with results per channel
        """
        if channels is None:
            channels = ['email']

        results = {}
        for channel_name in channels:
            if channel_name not in NotificationService.CHANNELS:
                results[channel_name] = {'success': False, 'error': 'Unknown channel'}
                continue

            channel_class = NotificationService.CHANNELS[channel_name]
            channel = channel_class()

            result = channel.send(
                recipient=recipient_email,
                subject=subject,
                message=message
            )

            results[channel_name] = result

        return {
            'success': all(r.get('success') for r in results.values()),
            'results': results
        }
