"""
Payment service with abstraction layer for multiple payment gateways.

Supports: Stripe, PayPal, Bank Transfer, Pay at Property, etc.
Can add new gateways without changing application code.
"""

from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Tuple
import logging

import stripe
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Payment, Refund
from apps.bookings.models import Booking
from apps.bookings.service import BookingService

logger = logging.getLogger(__name__)

# Payment statuses that mean money was actually received (and may be refunded).
REFUNDABLE_PAYMENT_STATUSES = ('paid', 'partially_refunded')
# Payment statuses from which a manual/webhook confirmation may still be applied.
OPEN_PAYMENT_STATUSES = ('pending', 'processing')


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


class PaymentGatewayError(Exception):
    """The payment gateway rejected or failed a request (safe message only)."""


class ManualConfirmationNotAllowed(ValueError):
    """Manual confirmation is not allowed for gateway-verified payment methods."""


class StripePaymentProcessor(PaymentProcessor):
    """
    Stripe payment processor using the official Stripe SDK.

    - Hosted Stripe Checkout (server-created session, server-side amount)
    - Webhooks verified with stripe.Webhook.construct_event over the raw body
      and the Stripe-Signature HTTP header
    - Real refunds via stripe.Refund.create against the PaymentIntent

    Keys are passed per request (api_key=...) - the global stripe.api_key is
    never set, and secrets are never logged.
    """

    CURRENCY = 'lkr'  # Server-side currency; LKR is a 2-decimal currency in Stripe

    def __init__(self, api_key: str, webhook_secret: str):
        self.api_key = api_key
        self.webhook_secret = webhook_secret

    @staticmethod
    def to_minor_units(amount: Decimal) -> int:
        """LKR 23,100.00 -> 2310000 (Stripe amounts are integers in minor units)."""
        return int((Decimal(amount) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

    def _require_api_key(self):
        if not self.api_key:
            raise PaymentGatewayError('Online card payments are not configured.')

    def initiate_payment(self, booking: Booking) -> Dict:
        """Not used directly - Checkout needs the Payment record for metadata/idempotency."""
        raise NotImplementedError('Use create_checkout_session(booking, payment)')

    def create_checkout_session(self, booking: Booking, payment: Payment) -> Dict:
        """
        Create a hosted Stripe Checkout Session for this payment.

        The amount and currency come only from the server-side Payment
        (= booking.total_price) - never from the browser.
        """
        self._require_api_key()
        metadata = {
            'booking_id': str(booking.id),
            'booking_reference': booking.booking_reference,
            'payment_id': str(payment.id),
        }
        success_url = f"{settings.SITE_URL}/bookings?payment=success&booking={booking.booking_reference}"
        cancel_url = f"{settings.SITE_URL}/bookings?payment=cancelled&booking={booking.booking_reference}"
        try:
            session = stripe.checkout.Session.create(
                api_key=self.api_key,
                idempotency_key=f'checkout-{payment.id}',
                mode='payment',
                payment_method_types=['card'],
                line_items=[{
                    'quantity': 1,
                    'price_data': {
                        'currency': self.CURRENCY,
                        'unit_amount': self.to_minor_units(payment.amount),
                        'product_data': {
                            'name': f'Booking {booking.booking_reference}',
                            'description': (
                                f'{booking.property.name} - {booking.room_type.name} '
                                f'({booking.check_in_date} to {booking.check_out_date})'
                            ),
                        },
                    },
                }],
                client_reference_id=booking.booking_reference,
                customer_email=booking.guest.email,
                metadata=metadata,
                payment_intent_data={'metadata': metadata},
                success_url=success_url,
                cancel_url=cancel_url,
            )
        except stripe.StripeError:
            logger.exception('Stripe Checkout Session creation failed for payment %s', payment.id)
            raise PaymentGatewayError('Could not start card payment. Please try again.')

        return {
            'session_id': session.id,
            'url': session.url,
            'expires_at': session.expires_at,
        }

    def verify_payment(self, payment_reference: str) -> Dict:
        """Look up a Checkout Session's payment status with Stripe."""
        self._require_api_key()
        try:
            session = stripe.checkout.Session.retrieve(payment_reference, api_key=self.api_key)
        except stripe.StripeError:
            logger.exception('Stripe session lookup failed for %s', payment_reference)
            raise PaymentGatewayError('Could not verify payment with Stripe.')
        return {
            'success': True,
            'status': 'paid' if session.payment_status == 'paid' else session.payment_status,
            'amount': Decimal(session.amount_total or 0) / 100,
        }

    def refund_payment(self, payment_reference: str, amount: Decimal, idempotency_key: str = None) -> Dict:
        """
        Refund real money through Stripe. payment_reference is the PaymentIntent
        id; the caller has already capped `amount` at the refundable balance.
        """
        self._require_api_key()
        try:
            refund = stripe.Refund.create(
                api_key=self.api_key,
                idempotency_key=idempotency_key,
                payment_intent=payment_reference,
                amount=self.to_minor_units(amount),
            )
        except stripe.StripeError:
            logger.exception('Stripe refund failed for PaymentIntent %s', payment_reference)
            raise PaymentGatewayError('The refund could not be processed by Stripe.')
        return {
            'success': True,
            'refund_reference': refund.id,
            'amount': amount,
            'gateway_status': refund.status,
        }

    def construct_event(self, payload: bytes, sig_header: str):
        """
        Verify a webhook with the official SDK over the RAW request body and
        the Stripe-Signature header. Raises stripe.SignatureVerificationError
        (bad/missing signature, stale timestamp) or ValueError (bad payload,
        or no webhook secret configured - fails closed).
        """
        if not self.webhook_secret:
            raise ValueError('Stripe webhook secret is not configured')
        return stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)

    def process_webhook(self, data: Dict) -> Dict:
        """Stripe webhooks are handled by PaymentService.handle_stripe_webhook (raw body + header)."""
        return {'success': False, 'error': 'Use the Stripe webhook endpoint'}


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
            # Secrets come from settings/environment only. A hardcoded webhook
            # secret in source would let anyone forge a "paid" webhook; an unset
            # secret makes signature verification fail closed.
            return processor_class(
                api_key=getattr(settings, 'STRIPE_LIVE_SECRET_KEY', ''),
                webhook_secret=getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
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

        with transaction.atomic():
            # Lock and re-read the booking: only a booking that still holds its
            # rooms and is not already paid may start a payment attempt.
            booking = Booking.objects.select_for_update().get(id=booking.id)
            if booking.status not in BookingService.PAYABLE_STATUSES:
                raise ValueError(f"Cannot start a payment for booking with status: {booking.status}")
            if booking.payment_status == 'paid':
                raise ValueError("This booking has already been paid.")

            # Idempotent: re-use an open attempt for the same method instead of
            # creating a duplicate payment record.
            payment = Payment.objects.select_for_update().filter(
                booking=booking, payment_method=payment_method, status__in=OPEN_PAYMENT_STATUSES
            ).first()

            if payment_method == 'stripe':
                payment, payment_url = PaymentService._stripe_checkout(processor, booking, payment)
            else:
                # Call processor
                result = processor.initiate_payment(booking)
                payment_url = result.get('payment_url')
                if payment is None:
                    # Amount is always the server-side booking total, never client input.
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
            'payment_url': payment_url,
            'payment_method': payment_method,
            'amount': payment.amount,
            'currency': 'LKR'
        }

    @staticmethod
    def _stripe_checkout(processor: 'StripePaymentProcessor', booking: Booking,
                         open_payment: Optional[Payment]) -> Tuple[Payment, str]:
        """
        Return (payment, checkout_url) for a Stripe payment. Re-uses the open
        attempt while its Checkout Session is still valid; otherwise creates a
        new Payment + Session. Caller holds the booking row lock.
        """
        if open_payment is not None:
            gateway = open_payment.gateway_response or {}
            expires_at = gateway.get('checkout_expires_at') or 0
            if gateway.get('checkout_url') and expires_at > timezone.now().timestamp():
                return open_payment, gateway['checkout_url']
            # Session expired (Stripe also sends checkout.session.expired) -
            # close this attempt so a fresh one can be created.
            open_payment.status = 'cancelled'
            open_payment.save(update_fields=['status', 'updated_at'])

        # Amount is always the server-side booking total, never client input.
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.total_price,
            status='pending',
            payment_method='stripe',
            gateway_name='stripe',
        )
        session = processor.create_checkout_session(booking, payment)
        payment.transaction_reference = session['session_id']
        payment.gateway_response = {
            'checkout_session_id': session['session_id'],
            'checkout_url': session['url'],
            'checkout_expires_at': session['expires_at'],
        }
        payment.save(update_fields=['transaction_reference', 'gateway_response', 'updated_at'])
        return payment, session['url']

    @staticmethod
    def confirm_payment(payment: Payment, transaction_details: Dict = None, status: str = 'paid') -> Dict:
        """
        Record the outcome of a payment (manual/offline confirmation).

        Args:
            payment: Payment object to confirm
            transaction_details: Additional transaction details
            status: Outcome - 'paid', 'failed' or 'cancelled'. Only 'paid'
                confirms the booking; a failed/cancelled outcome never does.

        Returns:
            Dict with confirmation details

        Raises:
            ValueError: invalid outcome, payment not open, or booking no
                longer holds its rooms (cancelled/rejected are never revived).
        """
        if status not in ('paid', 'failed', 'cancelled'):
            raise ValueError(f"Invalid payment outcome: {status}")

        with transaction.atomic():
            # Lock and re-read both rows so the checks below see current state.
            payment = Payment.objects.select_for_update().get(id=payment.id)
            booking = Booking.objects.select_for_update().get(id=payment.booking_id)

            # Card payments are only ever settled by a verified Stripe webhook -
            # nobody (owner or admin) may record their outcome by hand.
            if payment.payment_method == 'stripe':
                raise ManualConfirmationNotAllowed(
                    'Card (Stripe) payments are confirmed automatically by Stripe and cannot be confirmed manually.'
                )

            if status == 'paid':
                # Idempotent: a repeated success confirmation changes nothing.
                if payment.status == 'paid':
                    return {'success': True, 'payment_id': payment.id, 'status': 'paid',
                            'message': 'Payment already confirmed'}
                if payment.status not in OPEN_PAYMENT_STATUSES:
                    raise ValueError(f"Cannot mark a payment with status '{payment.status}' as paid")
                # Only a booking that still holds its rooms can be confirmed -
                # never resurrect a cancelled/rejected booking (inventory integrity).
                if booking.status not in BookingService.PAYABLE_STATUSES:
                    raise ValueError(f"Cannot confirm payment for booking with status: {booking.status}")

                payment.status = 'paid'
                payment.gateway_response = transaction_details or {}
                payment.save()

                booking.payment_status = 'paid'
                booking.status = 'confirmed'
                booking.save()

                return {'success': True, 'payment_id': payment.id, 'status': 'paid',
                        'message': 'Payment confirmed'}

            # Failed / cancelled outcome: never marks anything paid and never
            # confirms the booking.
            if payment.status not in OPEN_PAYMENT_STATUSES:
                raise ValueError(f"Cannot mark a payment with status '{payment.status}' as {status}")

            payment.status = status
            payment.gateway_response = transaction_details or {}
            payment.save()

            # Keep booking.payment_status consistent, unless another payment
            # for this booking already succeeded.
            if booking.payment_status != 'paid':
                booking.payment_status = status
                booking.save()

        return {'success': True, 'payment_id': payment.id, 'status': status,
                'message': f'Payment marked as {status}'}

    @staticmethod
    def refundable_amount(payment: Payment) -> Decimal:
        """
        Maximum amount that may still be refunded for this payment:
        amount actually paid minus every refund already recorded against it
        (pending/processing/completed - only failed refunds are excluded).
        """
        if payment.status not in REFUNDABLE_PAYMENT_STATUSES:
            return Decimal('0')
        already_refunded = Refund.objects.filter(payment=payment).exclude(
            status='failed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        return max(payment.amount - already_refunded, Decimal('0'))

    @staticmethod
    def validate_refund_amount(payment: Payment, amount: Optional[Decimal]) -> Decimal:
        """
        Server-side refund limit: amount <= paid - already refunded.
        None means "refund everything still refundable". Caller must hold a
        row lock on the payment.
        """
        if payment.status not in REFUNDABLE_PAYMENT_STATUSES:
            raise ValueError(f"Cannot refund payment with status: {payment.status}")

        refundable = PaymentService.refundable_amount(payment)
        if amount is None:
            amount = refundable
        if amount <= 0:
            raise ValueError("Refund amount must be greater than zero.")
        if amount > refundable:
            raise ValueError(
                f"Refund amount ({amount}) exceeds the refundable balance ({refundable}) "
                f"for this payment (paid {payment.amount})."
            )
        return amount

    @staticmethod
    def process_refund(payment: Payment, amount: Decimal = None, reason: str = 'Guest cancellation') -> Dict:
        """
        Process a refund for a payment.

        Args:
            payment: Payment to refund
            amount: Amount to refund (default: the full remaining refundable balance)
            reason: Reason stored on the refund record

        Returns:
            Dict with refund details

        Raises:
            ValueError: payment not refundable, or amount <= 0 or above the
                remaining refundable balance.
        """
        with transaction.atomic():
            # Lock the payment so concurrent refunds can't both pass the cap.
            payment = Payment.objects.select_for_update().get(id=payment.id)
            amount = PaymentService.validate_refund_amount(payment, amount)

            service = PaymentService()
            processor = service.get_processor(payment.gateway_name)

            # Process refund
            if payment.gateway_name == 'stripe':
                # Real money moves through Stripe against the PaymentIntent that
                # the verified webhook recorded. The idempotency key is derived
                # from the already-refunded total, so a retried request (e.g.
                # after a timeout) returns the same Stripe refund, never a second one.
                payment_intent = (payment.gateway_response or {}).get('payment_intent')
                if not payment_intent:
                    raise ValueError('This card payment has no Stripe PaymentIntent on record and cannot be refunded.')
                already_refunded = payment.amount - PaymentService.refundable_amount(payment)
                result = processor.refund_payment(
                    payment_intent, amount,
                    idempotency_key=f'refund-{payment.id}-{already_refunded}-{amount}'
                )
                refund_status = 'completed' if result.get('gateway_status') == 'succeeded' else 'processing'
            else:
                # Offline methods (pay at property / bank transfer): the refund
                # is recorded and handed over outside the system - unchanged.
                result = processor.refund_payment(payment.transaction_reference, amount)
                refund_status = 'processing'

            # Create refund record
            refund = Refund.objects.create(
                booking=payment.booking,
                payment=payment,
                amount=amount,
                reason=reason or 'Guest cancellation',
                status=refund_status
            )

            # Update payment status from the cumulative refunded total
            if PaymentService.refundable_amount(payment) <= 0:
                payment.status = 'refunded'
            else:
                payment.status = 'partially_refunded'
            payment.save()

        return {
            'success': True,
            'refund_id': refund.id,
            'amount': amount,
            'status': refund.status,
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
        # Only gateways with their own verified webhook flow may change payment
        # state; Stripe uses handle_stripe_webhook (raw body + signature header).
        # Offline processors (bank transfer, pay at property) have no webhooks.
        service = PaymentService()
        processor = service.get_processor(gateway)
        result = processor.process_webhook(data)
        if result.get('success'):
            # No current non-Stripe processor reports success; refuse rather
            # than apply an unverified state change.
            logger.error('Unexpected successful webhook result from gateway %s - ignored', gateway)
            return {'success': False, 'error': 'Webhook not supported for this gateway'}
        return result

    # Events the Stripe Checkout flow needs. Card-only Checkout settles
    # synchronously, so checkout.session.completed (payment_status='paid') is
    # the success signal and checkout.session.expired closes an abandoned
    # attempt. Failed card attempts do not end a Checkout Session (the guest
    # can retry on the same page), so payment_intent.* events are not needed.
    STRIPE_HANDLED_EVENTS = ('checkout.session.completed', 'checkout.session.expired')
    MAX_STORED_EVENT_IDS = 20

    @staticmethod
    def handle_stripe_webhook(payload: bytes, sig_header: Optional[str]) -> Tuple[int, Dict]:
        """
        Verify and apply a Stripe webhook.

        Args:
            payload: the RAW request body bytes (never re-serialized JSON)
            sig_header: the Stripe-Signature HTTP header

        Returns:
            (http_status, body). 400 for missing/invalid signature or payload;
            200 for every verified event - including duplicates, unknown
            sessions and ignored event types - so Stripe stops retrying.
        """
        if not sig_header:
            return 400, {'success': False, 'error': 'Missing Stripe-Signature header'}

        processor = PaymentService().get_processor('stripe')
        try:
            event = processor.construct_event(payload, sig_header)
        except stripe.SignatureVerificationError:
            logger.warning('Rejected Stripe webhook: invalid signature')
            return 400, {'success': False, 'error': 'Invalid signature'}
        except ValueError:
            logger.warning('Rejected Stripe webhook: invalid payload or webhook secret not configured')
            return 400, {'success': False, 'error': 'Invalid payload'}

        event_type = event['type']
        if event_type not in PaymentWebhookHandler.STRIPE_HANDLED_EVENTS:
            return 200, {'success': True, 'ignored': event_type}

        # stripe>=13 StripeObjects are not dicts - work on a plain copy.
        session = event['data']['object'].to_dict()
        if event_type == 'checkout.session.completed':
            return 200, PaymentWebhookHandler._stripe_checkout_completed(event['id'], session)
        return 200, PaymentWebhookHandler._stripe_checkout_expired(event['id'], session)

    @staticmethod
    def _record_event(payment: Payment, event_id: str, **extra) -> Dict:
        """Remember processed Stripe event ids on the payment (duplicate detection)."""
        gateway = dict(payment.gateway_response or {})
        event_ids = list(gateway.get('stripe_event_ids', []))
        event_ids.append(event_id)
        gateway['stripe_event_ids'] = event_ids[-PaymentWebhookHandler.MAX_STORED_EVENT_IDS:]
        gateway.update(extra)
        return gateway

    @staticmethod
    def _lock_stripe_payment(session_id: str) -> Optional[Payment]:
        return Payment.objects.select_for_update().filter(
            transaction_reference=session_id, payment_method='stripe'
        ).first()

    @staticmethod
    def _stripe_checkout_completed(event_id: str, session) -> Dict:
        newly_confirmed_payment = None

        with transaction.atomic():
            payment = PaymentWebhookHandler._lock_stripe_payment(session['id'])
            if payment is None:
                # Not one of ours (e.g. another integration on the same account).
                logger.warning('Stripe checkout.session.completed for unknown session - ignored')
                return {'success': True, 'matched': False}
            booking = Booking.objects.select_for_update().get(id=payment.booking_id)
            response = {'success': True, 'payment_id': payment.id, 'booking_id': booking.id}

            # Idempotent: Stripe retries and may deliver an event more than
            # once. Same event id, or a payment that already left the open
            # states, changes nothing (no double-confirm, no second email).
            gateway = payment.gateway_response or {}
            if event_id in gateway.get('stripe_event_ids', []) or payment.status not in OPEN_PAYMENT_STATUSES:
                response.update(status=payment.status, duplicate=True)
                return response

            if session.get('payment_status') != 'paid':
                # Session finished without captured money - never mark paid.
                payment.status = 'processing'
                payment.gateway_response = PaymentWebhookHandler._record_event(payment, event_id)
                payment.save()
                response.update(status='processing', booking_confirmed=False)
                return response

            # The amount Stripe charged must be exactly the server-side amount.
            expected = StripePaymentProcessor.to_minor_units(payment.amount)
            if session.get('amount_total') != expected or (session.get('currency') or '').lower() != StripePaymentProcessor.CURRENCY:
                payment.error_message = (
                    f"Stripe charged {session.get('amount_total')} {session.get('currency')}, "
                    f"expected {expected} {StripePaymentProcessor.CURRENCY}. Booking not confirmed - review required."
                )
                payment.gateway_response = PaymentWebhookHandler._record_event(payment, event_id)
                payment.save()
                logger.error('Stripe amount mismatch for payment %s - booking not confirmed', payment.id)
                response.update(status=payment.status, booking_confirmed=False, requires_review=True)
                return response

            payment.status = 'paid'
            payment.gateway_response = PaymentWebhookHandler._record_event(
                payment, event_id, payment_intent=session.get('payment_intent')
            )

            if booking.status not in BookingService.PAYABLE_STATUSES:
                # Money was captured for a booking that no longer holds its
                # rooms (cancelled/rejected). Record the payment truthfully so
                # it can be refunded, but NEVER revive the booking.
                payment.error_message = (
                    f"Payment received for booking in status '{booking.status}'. "
                    f"Booking was not confirmed - refund required."
                )
                payment.save()
                logger.warning(
                    'Stripe payment %s received for %s booking %s - booking not revived, refund required',
                    payment.id, booking.status, booking.id
                )
                response.update(status='paid', booking_confirmed=False, requires_refund=True)
                return response

            payment.save()
            booking.payment_status = 'paid'
            booking.status = 'confirmed'
            booking.save()
            response.update(status='paid', booking_confirmed=True)
            newly_confirmed_payment = payment

        # After commit: email once per newly confirmed payment. A failure is
        # logged and never undoes the saved payment.
        if newly_confirmed_payment is not None:
            send_payment_confirmation_email(newly_confirmed_payment)
        return response

    @staticmethod
    def _stripe_checkout_expired(event_id: str, session) -> Dict:
        with transaction.atomic():
            payment = PaymentWebhookHandler._lock_stripe_payment(session['id'])
            if payment is None:
                return {'success': True, 'matched': False}
            gateway = payment.gateway_response or {}
            if event_id in gateway.get('stripe_event_ids', []) or payment.status not in OPEN_PAYMENT_STATUSES:
                return {'success': True, 'payment_id': payment.id, 'status': payment.status, 'duplicate': True}

            # Abandoned checkout: close the attempt (never paid). The booking is
            # unchanged, so the guest can start a new payment.
            payment.status = 'cancelled'
            payment.gateway_response = PaymentWebhookHandler._record_event(payment, event_id)
            payment.save()
            return {'success': True, 'payment_id': payment.id, 'status': 'cancelled'}


def send_payment_confirmation_email(payment: Payment) -> None:
    """
    Send the guest's payment-received email. Called only after the payment is
    committed and only for a NEW confirmation (idempotent callers). Failures
    are logged and never affect the saved payment.
    """
    try:
        from apps.notifications.service import NotificationService
        NotificationService.send_payment_confirmation(payment.booking, payment.amount, payment=payment)
    except Exception:
        logger.exception('Failed to send payment-confirmation email for payment %s', payment.id)
