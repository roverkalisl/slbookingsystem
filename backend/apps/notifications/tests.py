"""
Tests for notification system.

Run with: python manage.py test apps.notifications
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from .models import Notification, NotificationTemplate
from .service import (
    NotificationService, EmailChannel, SMSChannel,
    PushNotificationChannel, InAppChannel
)
from apps.core.models import Role, UserRole
from apps.properties.models import Property, PropertyType, RoomType, Pricing
from apps.bookings.models import Booking

User = get_user_model()


class EmailChannelTestCase(TestCase):
    """Tests for email notification channel"""

    def setUp(self):
        """Set up test data"""
        self.channel = EmailChannel()
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.guest = User.objects.create_user(
            email='guest@example.com',
            password='test',
            first_name='John',
            last_name='Doe'
        )
        UserRole.objects.create(user=self.guest, role=guest_role)

    @patch('django.core.mail.send_mail')
    def test_send_email(self, mock_send):
        """Test sending email notification"""
        mock_send.return_value = 1

        result = self.channel.send(
            recipient=self.guest,
            title='Booking Confirmed',
            message='Your booking has been confirmed',
            template_context={
                'booking_id': 'BK001',
                'check_in': '2026-09-20',
                'total_price': '5000.00'
            }
        )

        self.assertTrue(result)
        mock_send.assert_called_once()

    def test_email_channel_supports_html(self):
        """Test email channel supports HTML templates"""
        supports_html = self.channel.supports_html_template

        self.assertTrue(supports_html)


class SMSChannelTestCase(TestCase):
    """Tests for SMS notification channel"""

    def setUp(self):
        """Set up test data"""
        self.channel = SMSChannel()
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.guest = User.objects.create_user(
            email='guest@example.com',
            password='test',
            phone_number='+94711234567'
        )
        UserRole.objects.create(user=self.guest, role=guest_role)

    @patch('twilio.rest.Client')
    def test_send_sms(self, mock_twilio):
        """Test sending SMS notification"""
        mock_client = MagicMock()
        mock_twilio.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(sid='SM123')

        result = self.channel.send(
            recipient=self.guest,
            title='Booking Confirmed',
            message='Your booking BK001 is confirmed. Check-in: 2026-09-20'
        )

        self.assertTrue(result)


class PushNotificationChannelTestCase(TestCase):
    """Tests for push notification channel"""

    def setUp(self):
        """Set up test data"""
        self.channel = PushNotificationChannel()
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.guest = User.objects.create_user(
            email='guest@example.com',
            password='test'
        )
        UserRole.objects.create(user=self.guest, role=guest_role)

    @patch('firebase_admin.messaging.send')
    def test_send_push(self, mock_firebase):
        """Test sending push notification"""
        mock_firebase.return_value = 'msg_123'

        result = self.channel.send(
            recipient=self.guest,
            title='Booking Confirmed',
            message='Your booking has been confirmed'
        )

        self.assertTrue(result)


class InAppChannelTestCase(TestCase):
    """Tests for in-app notification channel"""

    def setUp(self):
        """Set up test data"""
        self.channel = InAppChannel()
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.guest = User.objects.create_user(
            email='guest@example.com',
            password='test'
        )
        UserRole.objects.create(user=self.guest, role=guest_role)

    def test_send_in_app_notification(self):
        """Test sending in-app notification"""
        result = self.channel.send(
            recipient=self.guest,
            title='Booking Confirmed',
            message='Your booking has been confirmed',
            notification_type='booking_confirmation',
            related_object_id='booking_123'
        )

        # In-app notifications are stored in database
        self.assertTrue(result)

        # Verify notification was created
        notification = Notification.objects.filter(
            recipient=self.guest,
            title='Booking Confirmed'
        ).first()

        self.assertIsNotNone(notification)
        self.assertEqual(notification.message, 'Your booking has been confirmed')


class NotificationServiceTestCase(TestCase):
    """Tests for notification service"""

    def setUp(self):
        """Set up test data"""
        guest_role, _ = Role.objects.get_or_create(name='guest')
        owner_role, _ = Role.objects.get_or_create(name='property_owner')

        self.guest = User.objects.create_user(
            email='guest@example.com',
            password='test',
            first_name='John'
        )
        UserRole.objects.create(user=self.guest, role=guest_role)

        self.owner = User.objects.create_user(
            email='owner@example.com',
            password='test',
            first_name='Property'
        )
        UserRole.objects.create(user=self.owner, role=owner_role)

        # Create booking setup
        property_type = PropertyType.objects.create(name='Villa')
        self.property = Property.objects.create(
            owner=self.owner,
            property_type=property_type,
            name='Test Property',
            city='Colombo',
            district='Western',
            province='Western',
            status='published'
        )

        self.room_type = RoomType.objects.create(
            property=self.property,
            name='Room',
            max_adults=2,
            total_occupancy=2,
            total_rooms=1
        )

        Pricing.objects.create(
            room_type=self.room_type,
            base_price=Decimal('5000.00')
        )

        self.check_in = date.today() + timedelta(days=7)
        self.check_out = self.check_in + timedelta(days=3)

    @patch('apps.notifications.service.EmailChannel.send')
    def test_booking_confirmation_notification(self, mock_email):
        """Test booking confirmation notification"""
        mock_email.return_value = True

        # Create booking
        self.booking = Booking.objects.create(
            room_type=self.room_type,
            guest=self.guest,
            check_in=self.check_in,
            check_out=self.check_out,
            num_adults=2,
            status='confirmed',
            total_price=Decimal('15000.00'),
            number_of_nights=3
        )

        # Send notification
        NotificationService.booking_confirmation(self.booking)

        # Verify in-app notification created
        notification = Notification.objects.filter(
            recipient=self.guest,
            notification_type='booking_confirmation'
        ).first()

        self.assertIsNotNone(notification)

    @patch('apps.notifications.service.EmailChannel.send')
    def test_booking_cancellation_notification(self, mock_email):
        """Test booking cancellation notification"""
        mock_email.return_value = True

        # Create and cancel booking
        self.booking = Booking.objects.create(
            room_type=self.room_type,
            guest=self.guest,
            check_in=self.check_in,
            check_out=self.check_out,
            num_adults=2,
            status='cancelled',
            total_price=Decimal('15000.00'),
            number_of_nights=3
        )

        # Send notification
        NotificationService.cancellation_notification(self.booking)

        # Verify notification created
        notification = Notification.objects.filter(
            recipient=self.guest,
            notification_type='booking_cancelled'
        ).first()

        self.assertIsNotNone(notification)

    @patch('apps.notifications.service.EmailChannel.send')
    def test_payment_confirmation_notification(self, mock_email):
        """Test payment confirmation notification"""
        mock_email.return_value = True

        # Create booking
        booking = Booking.objects.create(
            room_type=self.room_type,
            guest=self.guest,
            check_in=self.check_in,
            check_out=self.check_out,
            num_adults=2,
            status='confirmed',
            total_price=Decimal('15000.00'),
            number_of_nights=3
        )

        # Send payment notification
        NotificationService.payment_confirmation(
            recipient=self.guest,
            booking=booking,
            amount=Decimal('15000.00'),
            payment_method='stripe'
        )

        # Verify notification created
        notification = Notification.objects.filter(
            recipient=self.guest,
            notification_type='payment_confirmation'
        ).first()

        self.assertIsNotNone(notification)

    @patch('apps.notifications.service.EmailChannel.send')
    def test_owner_notification(self, mock_email):
        """Test owner notification"""
        mock_email.return_value = True

        # Create booking
        booking = Booking.objects.create(
            room_type=self.room_type,
            guest=self.guest,
            check_in=self.check_in,
            check_out=self.check_out,
            num_adults=2,
            status='confirmed',
            total_price=Decimal('15000.00'),
            number_of_nights=3
        )

        # Send owner notification
        NotificationService.owner_notification(
            recipient=self.owner,
            booking=booking,
            message_type='new_booking'
        )

        # Verify notification created for owner
        notification = Notification.objects.filter(
            recipient=self.owner,
            notification_type='owner_new_booking'
        ).first()

        self.assertIsNotNone(notification)


class NotificationTemplateTestCase(TestCase):
    """Tests for notification templates"""

    def setUp(self):
        """Set up test data"""
        self.template = NotificationTemplate.objects.create(
            notification_type='booking_confirmation',
            subject='Booking Confirmed - {{booking_id}}',
            template='Your booking {{booking_id}} is confirmed. Check-in: {{check_in}}'
        )

    def test_template_variable_substitution(self):
        """Test template variable substitution"""
        context = {
            'booking_id': 'BK001',
            'check_in': '2026-09-20'
        }

        message = self.template.render(context)

        self.assertIn('BK001', message)
        self.assertIn('2026-09-20', message)
        self.assertNotIn('{{', message)

    def test_template_html_rendering(self):
        """Test HTML template rendering"""
        html_template = NotificationTemplate.objects.create(
            notification_type='booking_confirmation_html',
            is_html=True,
            subject='Booking Confirmed',
            template='<p>Your booking {{booking_id}} is confirmed.</p>'
        )

        self.assertTrue(html_template.is_html)
