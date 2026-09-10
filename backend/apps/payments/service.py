"""
Payment service with abstraction layer for multiple payment gateways.

Supports: Stripe, PayPal, Bank Transfer, Pay at Property, etc.
Can add new gateways without changing application code.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Optional
import hashlib
import hmac
import json

from .models import Payment, Refund
from apps.bookings.models import Booking


class PaymentProcessor(ABC):
    """Abstract base class for payment processors"""

    @abstractmethod
    def initiate_payment(self, booking: Booking) -> Dict:
        """
        Initiate a payment and return payment details.

        Returns:
            {
                'success': bool,
                'payment_url': str (if applicable),
                'payment_id': str,
                'payment_reference': str
            }
        """
        pass

    @abstractmethod
    def verify_payment(self, payment_reference: str) -> Dict:
        """
        Verify if a payment was successful.

        Returns:
            {
                'success': bool,
                'status': str,
                'amount': Decimal
            }
        """
        pass

    @abstractmethod
    def refund_payment(self, payment_reference: str, amount: Decimal) -> Dict:
        """
        Refund a payment.

        Returns:
            {
                'success': bool,
                'refund_reference': str,
                'amount': Decimal
            }
        """
        pass

    @abstractmethod
    def process_webhook(self, data: Dict) -> Dict:
        """
        Process a webhook from the payment gateway.

        Returns:
            {
                'success': bool,
                'payment_reference': str,
                'status': str,
                'error': str (if applicable)
            }
        """
        pass


class StripePaymentProcessor(PaymentProcessor):
    """Stripe payment processor"""

    def __init__(self, api_key: str, webhook_secret: str):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        # In production, use: import stripe; stripe.api_key = api_key

    def initiate_payment(self, booking: Booking) -> Dict:
        """
        Create a Stripe payment session.

        In production, would call Stripe API:
        session = stripe.checkout.Session.create(...)
        """
        # Placeholder: In real implementation, call Stripe API
        payment_id = f"stripe_{booking.id}"

        return {
            'success': True,
            'payment_url': f"https://checkout.stripe.com/pay/{payment_id}",
            'payment_id': payment_id,
            'payment_reference': payment_id
        }

    def verify_payment(self, payment_reference: str) -> Dict:
        """Verify payment status with Stripe"""
        # Placeholder: In real implementation, call Stripe API
        return {
            'success': True,
            'status': 'paid',
            'amount': Decimal('0')
        }

    def refund_payment(self, payment_reference: str, amount: Decimal) -> Dict:
        """Refund a Stripe payment"""
        # Placeholder: In real implementation, call Stripe API
        return {
            'success': True,
            'refund_reference': f"{payment_reference}_refund",
            'amount': amount
        }

    def process_webhook(self, data: Dict) -> Dict:
        """
        Process Stripe webhook.

        Verifies signature and processes payment events.
        """
        # Verify webhook signature
        signature = data.get('signature')
        body = data.get('body')

        if not self._verify_signature(signature, body):
            return {'success': False, 'error': 'Invalid signature'}

        event_data = json.loads(body)
        event_type = event_data.get('type')

        if event_type == 'checkout.session.completed':
            session = event_data['data']['object']
            return {
                'success': True,
                'payment_reference': session['id'],
                'status': 'paid'
            }

        return {'success': False, 'error': 'Unknown event type'}

    def _verify_signature(self, signature: str, body: str) -> bool:
        """Verify Stripe webhook signature"""
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)


class PayAtPropertyProcessor(PaymentProcessor):
    """Pay at property (no online payment processing)"""

    def initiate_payment(self, booking: Booking) -> Dict:
        """
        Pay at property - no payment processing needed.
        Booking is confirmed, payment collected at check-in.
        """
        return {
            'success': True,
            'payment_url': None,
            'payment_id': f"pay_at_property_{booking.id}",
            'payment_reference': f"pay_at_property_{booking.id}"
        }

    def verify_payment(self, payment_reference: str) -> Dict:
        """Payment verified when owner confirms guest paid"""
        return {
            'success': True,
            'status': 'pending',  # Waiting for property owner confirmation
            'amount': Decimal('0')
        }

    def refund_payment(self, payment_reference: str, amount: Decimal) -> Dict:
        """Record refund to be given at property"""
        return {
            'success': True,
            'refund_reference': f"{payment_reference}_refund",
            'amount': amount,
            'note': 'Refund to be given at property'
        }

    def process_webhook(self, data: Dict) -> Dict:
        """No webhooks for pay at property"""
        return {'success': False, 'error': 'No webhooks for this payment method'}


class BankTransferProcessor(PaymentProcessor):
    """Bank transfer payment processor"""

    def __init__(self, account_details: Dict):
        self.account_details = account_details

    def initiate_payment(self, booking: Booking) -> Dict:
        """
        Return bank details for transfer.
        Booking reference used as transfer note.
        """
        return {
            'success': True,
            'payment_url': None,
            'payment_id': f"bank_transfer_{booking.id}",
            'payment_reference': booking.booking_reference,
            'account_details': self.account_details,
            'note': f"Transfer reference: {booking.booking_reference}"
        }

    def verify_payment(self, payment_reference: str) -> Dict:
        """Bank transfers must be verified manually or via bank API"""
        return {
            'success': True,
            'status': 'pending_verification',
            'amount': Decimal('0')
        }

    def refund_payment(self, payment_reference: str, amount: Decimal) -> Dict:
        """Refund via bank transfer"""
        return {
            'success': True,
            'refund_reference': f"{payment_reference}_refund",
            'amount': amount,
            'note': 'Refund will be transferred to guest bank account'
        }

    def process_webhook(self, data: Dict) -> Dict:
        """No webhooks for bank transfers"""
        return {'success': False, 'error': 'No webhooks for this payment method'}


class PaymentService:
    """Service for handling payments with multiple processors"""

    PROCESSORS = {
        'stripe': StripePaymentProcessor,
        'pay_at_property': PayAtPropertyProcessor,
        'bank_transfer': BankTransferProcessor,
        # Add more: 'paypal': PayPalPaymentProcessor, etc.
    }

    def __init__(self):
        self._processor_instances = {}

    def register_processor(self, method_name: str, processor: PaymentProcessor):
        """Register a payment processor"""
        self._processor_instances[method_name] = processor

    def get_processor(self, method_name: str) -> PaymentProcessor:
        """Get a payment processor instance"""
        if method_name in self._processor_instances:
            return self._processor_instances[method_name]

        processor_class = self.PROCESSORS.get(method_name)
        if not processor_class:
            raise ValueError(f"Unknown payment method: {method_name}")

        # Create instance (in production, would load config)
        if method_name == 'stripe':
            return processor_class(
                api_key='sk_live_xxxxx',  # From settings
                webhook_secret='whsec_xxxxx'  # From settings
            )
        elif method_name == 'bank_transfer':
            return processor_class(
                account_details={
                    'account_name': 'SL Booking',
                    'account_number': '1234567890',
                    'bank_code': '123',
                    'currency': 'LKR'
                }
            )

        return processor_class()

    @staticmethod
    def initiate_payment(booking: Booking, payment_method: str = 'stripe') -> Dict:
        """
        Initiate payment for a booking.

        Args:
            booking: Booking object
            payment_method: Payment method name (stripe, pay_at_property, bank_transfer)

        Returns:
            Dict with payment initiation details
        """
        service = PaymentService()
        processor = service.get_processor(payment_method)

        # Call processor
        result = processor.initiate_payment(booking)

        # Create payment record
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.total_price,
            status='pending',
            payment_method=payment_method,
            transaction_reference=result.get('payment_reference'),
            gateway_name=payment_method
        )

        return {
            'success': True,
            'payment_id': payment.id,
            'payment_url': result.get('payment_url'),
            'payment_method': payment_method,
            'amount': booking.total_price,
            'currency': 'LKR'
        }

    @staticmethod
    def confirm_payment(payment: Payment, transaction_details: Dict = None) -> Dict:
        """
        Confirm a payment.

        Args:
            payment: Payment object to confirm
            transaction_details: Additional transaction details

        Returns:
            Dict with confirmation details
        """
        payment.status = 'paid'
        payment.gateway_response = transaction_details or {}
        payment.save()

        # Update booking status
        booking = payment.booking
        booking.payment_status = 'paid'
        booking.status = 'confirmed'
        booking.save()

        return {
            'success': True,
            'payment_id': payment.id,
            'status': 'paid',
            'message': 'Payment confirmed'
        }

    @staticmethod
    def process_refund(payment: Payment, amount: Decimal = None) -> Dict:
        """
        Process a refund for a payment.

        Args:
            payment: Payment to refund
            amount: Amount to refund (default: full amount)

        Returns:
            Dict with refund details
        """
        if amount is None:
            amount = payment.amount

        service = PaymentService()
        processor = service.get_processor(payment.gateway_name)

        # Process refund
        result = processor.refund_payment(payment.transaction_reference, amount)

        # Create refund record
        refund = Refund.objects.create(
            booking=payment.booking,
            payment=payment,
            amount=amount,
            reason='Guest cancellation',
            status='processing'
        )

        # Update payment status
        if amount >= payment.amount:
            payment.status = 'refunded'
        else:
            payment.status = 'partially_refunded'
        payment.save()

        return {
            'success': True,
            'refund_id': refund.id,
            'amount': amount,
            'status': 'processing',
            'refund_reference': result.get('refund_reference')
        }


class PaymentWebhookHandler:
    """Handle webhooks from payment gateways"""

    @staticmethod
    def handle_webhook(gateway: str, data: Dict) -> Dict:
        """
        Handle payment webhook.

        Args:
            gateway: Payment gateway name (stripe, etc.)
            data: Webhook data

        Returns:
            Dict with processing result
        """
        service = PaymentService()
        processor = service.get_processor(gateway)

        # Process webhook
        result = processor.process_webhook(data)

        if not result.get('success'):
            return result

        # Find and update payment
        payment_reference = result.get('payment_reference')
        try:
            payment = Payment.objects.get(transaction_reference=payment_reference)

            # Update payment
            payment.status = result.get('status')
            payment.gateway_response = data
            payment.save()

            # Update booking if paid
            if result.get('status') == 'paid':
                booking = payment.booking
                booking.payment_status = 'paid'
                booking.status = 'confirmed'
                booking.save()

                # TODO: Send confirmation email

            return {
                'success': True,
                'payment_id': payment.id,
                'booking_id': payment.booking.id,
                'status': result.get('status')
            }

        except Payment.DoesNotExist:
            return {
                'success': False,
                'error': f"Payment not found: {payment_reference}"
            }
