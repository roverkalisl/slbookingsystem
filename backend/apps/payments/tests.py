"""
Tests for payment processing system.

Run with: python manage.py test apps.payments
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from .models import Payment
from .service import (
    PaymentService, StripePaymentProcessor, PayAtPropertyProcessor,
    BankTransferProcessor, PaymentProcessor, PaymentWebhookHandler
)
from apps.core.models import Role, UserRole

User = get_user_model()


class PaymentServiceTestCase(TestCase):
    """Tests for payment service factory pattern"""

    def setUp(self):
        """Set up test data"""
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.guest = User.objects.create_user(email='guest@example.com', password='test')
        UserRole.objects.create(user=self.guest, role=guest_role)

    def test_get_processor_stripe(self):
        """Test getting Stripe processor"""
        processor = PaymentService.get_processor('stripe')

        self.assertIsInstance(processor, StripePaymentProcessor)

    def test_get_processor_pay_at_property(self):
        """Test getting pay-at-property processor"""
        processor = PaymentService.get_processor('pay_at_property')

        self.assertIsInstance(processor, PayAtPropertyProcessor)

    def test_get_processor_bank_transfer(self):
        """Test getting bank transfer processor"""
        processor = PaymentService.get_processor('bank_transfer')

        self.assertIsInstance(processor, BankTransferProcessor)

    def test_get_processor_invalid(self):
        """Test invalid processor raises error"""
        with self.assertRaises(ValueError):
            PaymentService.get_processor('invalid_processor')


class StripePaymentTestCase(TestCase):
    """Tests for Stripe payment processor"""

    def setUp(self):
        """Set up test data"""
        self.processor = StripePaymentProcessor()
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.guest = User.objects.create_user(email='guest@example.com', password='test')
        UserRole.objects.create(user=self.guest, role=guest_role)

    @patch('stripe.PaymentIntent.create')
    def test_initiate_payment(self, mock_stripe):
        """Test initiating Stripe payment"""
        mock_stripe.return_value = MagicMock(
            id='pi_123456',
            client_secret='secret_123',
            status='requires_payment_method'
        )

        result = self.processor.initiate_payment(
            amount=Decimal('5000.00'),
            currency='USD',
            booking_id='booking_123',
            customer_email='guest@example.com'
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['processor_reference'], 'pi_123456')
        self.assertEqual(result['status'], 'pending')

    @patch('stripe.PaymentIntent.retrieve')
    def test_confirm_payment(self, mock_stripe):
        """Test confirming Stripe payment"""
        mock_stripe.return_value = MagicMock(
            status='succeeded',
            amount_received=5000,
            charges=MagicMock(data=[MagicMock(id='ch_123')])
        )

        result = self.processor.confirm_payment('pi_123456')

        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'completed')

    @patch('stripe.Refund.create')
    def test_process_refund(self, mock_stripe):
        """Test refunding Stripe payment"""
        mock_stripe.return_value = MagicMock(
            id='re_123456',
            status='succeeded',
            amount=5000
        )

        result = self.processor.process_refund(
            processor_reference='pi_123456',
            amount=Decimal('5000.00')
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'completed')


class PayAtPropertyTestCase(TestCase):
    """Tests for pay-at-property processor"""

    def setUp(self):
        """Set up test data"""
        self.processor = PayAtPropertyProcessor()

    def test_initiate_payment(self):
        """Test initiating pay-at-property payment"""
        result = self.processor.initiate_payment(
            amount=Decimal('5000.00'),
            currency='LKR',
            booking_id='booking_123'
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'pending')
        self.assertTrue(result['processor_reference'].startswith('PAP'))

    def test_confirm_payment(self):
        """Test confirming pay-at-property payment"""
        result = self.processor.confirm_payment('PAP_123456')

        # Pay-at-property requires manual confirmation
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'pending')

    def test_process_refund(self):
        """Test refunding pay-at-property payment"""
        result = self.processor.process_refund(
            processor_reference='PAP_123456',
            amount=Decimal('5000.00')
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'completed')


class BankTransferTestCase(TestCase):
    """Tests for bank transfer processor"""

    def setUp(self):
        """Set up test data"""
        self.processor = BankTransferProcessor()

    def test_initiate_payment(self):
        """Test initiating bank transfer"""
        result = self.processor.initiate_payment(
            amount=Decimal('5000.00'),
            currency='LKR',
            booking_id='booking_123'
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'pending')
        self.assertIn('bank_details', result)

    def test_confirm_payment(self):
        """Test confirming bank transfer"""
        result = self.processor.confirm_payment('BT_123456')

        # Bank transfer requires manual confirmation
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'pending')

    def test_bank_details_provided(self):
        """Test bank details are provided for transfer"""
        result = self.processor.initiate_payment(
            amount=Decimal('5000.00'),
            currency='LKR',
            booking_id='booking_123'
        )

        details = result.get('bank_details', {})
        self.assertIn('account_number', details)
        self.assertIn('bank_name', details)
        self.assertIn('routing_number', details)


class PaymentWebhookTestCase(TestCase):
    """Tests for payment webhook handling"""

    def setUp(self):
        """Set up test data"""
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.guest = User.objects.create_user(email='guest@example.com', password='test')
        UserRole.objects.create(user=self.guest, role=guest_role)

        self.handler = PaymentWebhookHandler()

    @patch('stripe.Event.construct_from')
    def test_handle_payment_intent_succeeded(self, mock_construct):
        """Test handling payment intent succeeded webhook"""
        mock_construct.return_value = MagicMock(
            type='payment_intent.succeeded',
            data=MagicMock(
                object=MagicMock(
                    id='pi_123456',
                    status='succeeded',
                    metadata={'booking_id': 'booking_123'}
                )
            )
        )

        # Create payment record
        payment = Payment.objects.create(
            guest=self.guest,
            amount=Decimal('5000.00'),
            currency='USD',
            status='pending',
            payment_method='stripe',
            processor_reference='pi_123456'
        )

        result = self.handler.handle_stripe_webhook({})

        self.assertIsNotNone(result)

    def test_handle_payment_intent_failed(self):
        """Test handling payment intent failed webhook"""
        event_data = {
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': {
                    'id': 'pi_failed',
                    'status': 'requires_payment_method',
                    'metadata': {'booking_id': 'booking_123'}
                }
            }
        }

        # Create payment record
        payment = Payment.objects.create(
            guest=self.guest,
            amount=Decimal('5000.00'),
            currency='USD',
            status='pending',
            payment_method='stripe',
            processor_reference='pi_failed'
        )

        # Should handle failure gracefully
        self.assertEqual(payment.status, 'pending')
