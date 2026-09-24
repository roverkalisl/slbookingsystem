"""
Stripe integration tests (official SDK).

- Webhooks: real Stripe-Signature header scheme (t=...,v1=HMAC-SHA256 over
  "{t}.{raw body}") verified by stripe.Webhook.construct_event - computed
  locally, no network.
- Checkout Sessions and Refunds: stripe API calls are MOCKED. The normal test
  suite never contacts Stripe and uses no real credentials.
- Payment confirmation email: template rendering, sent once, never blocks a
  saved payment.

Run with: python manage.py test apps.bookings.tests_stripe
"""

import hashlib
import hmac
import json
import time
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

import stripe
from django.core import mail
from django.template.loader import render_to_string
from django.test import override_settings

from apps.notifications.service import NotificationService
from apps.payments.models import Payment, Refund
from apps.payments.service import PaymentService
from .service import BookingService
from .tests_payment_security import PaymentTestBase

WEBHOOK_SECRET = 'whsec_unit_test_only'
TEST_API_KEY = 'sk_test_unit_test_only'
SITE = 'https://site.example'
WEBHOOK_URL = '/api/payments/webhook/stripe/'

STRIPE_SETTINGS = dict(
    STRIPE_WEBHOOK_SECRET=WEBHOOK_SECRET,
    STRIPE_LIVE_SECRET_KEY=TEST_API_KEY,
    SITE_URL=SITE,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)


def stripe_signature(payload: str, secret: str = WEBHOOK_SECRET, timestamp: int = None) -> str:
    """Build a Stripe-Signature header exactly as Stripe does."""
    timestamp = timestamp or int(time.time())
    signed = f'{timestamp}.{payload}'.encode()
    digest = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f't={timestamp},v1={digest}'


@override_settings(**STRIPE_SETTINGS)
class StripeTestBase(PaymentTestBase):
    SESSION_ID = 'cs_test_session_123'
    PAYMENT_INTENT = 'pi_test_123'

    def setUp(self):
        super().setUp()
        mail.outbox = []

    def make_stripe_payment(self, status='pending', payment_intent=None):
        gateway = {'checkout_session_id': self.SESSION_ID}
        if payment_intent:
            gateway['payment_intent'] = payment_intent
        payment = self.make_payment(status=status, method='stripe', reference=self.SESSION_ID)
        payment.gateway_response = gateway
        payment.save()
        return payment

    def event_payload(self, event_type='checkout.session.completed', event_id='evt_1', **session):
        obj = {
            'id': self.SESSION_ID,
            'object': 'checkout.session',
            'payment_status': 'paid',
            'amount_total': 2310000,  # LKR 23,100.00 in minor units
            'currency': 'lkr',
            'payment_intent': self.PAYMENT_INTENT,
        }
        obj.update(session)
        return json.dumps({'id': event_id, 'object': 'event', 'type': event_type, 'data': {'object': obj}})

    def post_webhook(self, payload, signature='auto'):
        self.client.force_authenticate(user=None)
        headers = {}
        if signature == 'auto':
            signature = stripe_signature(payload)
        if signature is not None:
            headers['HTTP_STRIPE_SIGNATURE'] = signature
        return self.client.generic('POST', WEBHOOK_URL, payload, content_type='application/json', **headers)

    def assert_booking(self, status, payment_status):
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, status)
        self.assertEqual(self.booking.payment_status, payment_status)


# ---------------------------------------------------------------------------
# Webhook signature verification
# ---------------------------------------------------------------------------

class StripeWebhookSignatureTestCase(StripeTestBase):

    def setUp(self):
        super().setUp()
        self.payment = self.make_stripe_payment()

    def assert_untouched(self):
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')
        self.assert_booking('pending', 'pending')

    def test_missing_stripe_signature_header_is_rejected(self):
        response = self.post_webhook(self.event_payload(), signature=None)
        self.assertEqual(response.status_code, 400)
        self.assert_untouched()

    def test_invalid_stripe_signature_is_rejected(self):
        response = self.post_webhook(self.event_payload(), signature=f't={int(time.time())},v1={"0" * 64}')
        self.assertEqual(response.status_code, 400)
        self.assert_untouched()

    def test_signature_with_wrong_secret_is_rejected(self):
        payload = self.event_payload()
        response = self.post_webhook(payload, signature=stripe_signature(payload, secret='whsec_attacker'))
        self.assertEqual(response.status_code, 400)
        self.assert_untouched()

    def test_old_placeholder_secret_is_rejected(self):
        payload = self.event_payload()
        response = self.post_webhook(payload, signature=stripe_signature(payload, secret='whsec_xxxxx'))
        self.assertEqual(response.status_code, 400)
        self.assert_untouched()

    def test_tampered_body_is_rejected(self):
        payload = self.event_payload()
        signature = stripe_signature(payload)
        tampered = payload.replace('2310000', '100')
        response = self.post_webhook(tampered, signature=signature)
        self.assertEqual(response.status_code, 400)
        self.assert_untouched()

    def test_stale_timestamp_is_rejected(self):
        payload = self.event_payload()
        old = int(time.time()) - 3600  # beyond the SDK's 300s tolerance (replay protection)
        response = self.post_webhook(payload, signature=stripe_signature(payload, timestamp=old))
        self.assertEqual(response.status_code, 400)
        self.assert_untouched()

    def test_signature_in_json_body_is_not_accepted(self):
        """The old placeholder scheme (signature inside the JSON body) must not work."""
        body = self.event_payload()
        legacy = json.dumps({'signature': hmac.new(WEBHOOK_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest(),
                             'body': body})
        response = self.post_webhook(legacy, signature=None)
        self.assertEqual(response.status_code, 400)
        self.assert_untouched()

    def test_invalid_payload_is_rejected(self):
        payload = 'not json'
        response = self.post_webhook(payload, signature=stripe_signature(payload))
        self.assertEqual(response.status_code, 400)
        self.assert_untouched()

    @override_settings(STRIPE_WEBHOOK_SECRET='')
    def test_unconfigured_webhook_secret_fails_closed(self):
        payload = self.event_payload()
        response = self.post_webhook(payload, signature=stripe_signature(payload, secret=''))
        self.assertEqual(response.status_code, 400)
        self.assert_untouched()

    def test_valid_webhook_is_processed(self):
        response = self.post_webhook(self.event_payload())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['booking_confirmed'])

    def test_webhook_works_with_csrf_enforcement(self):
        """Stripe sends no CSRF token or Bearer JWT - the signature is its authentication."""
        from rest_framework.test import APIClient
        payload = self.event_payload()
        client = APIClient(enforce_csrf_checks=True)
        response = client.generic('POST', WEBHOOK_URL, payload, content_type='application/json',
                                  HTTP_STRIPE_SIGNATURE=stripe_signature(payload))
        self.assertEqual(response.status_code, 200, response.content)


# ---------------------------------------------------------------------------
# Webhook events: success, failure, idempotency, booking-status guard
# ---------------------------------------------------------------------------

class StripeWebhookEventTestCase(StripeTestBase):

    def setUp(self):
        super().setUp()
        self.payment = self.make_stripe_payment()

    def test_successful_payment_marks_paid_and_confirms_booking(self):
        response = self.post_webhook(self.event_payload())
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')
        self.assertEqual(self.payment.gateway_response['payment_intent'], self.PAYMENT_INTENT)
        self.assert_booking('confirmed', 'paid')

    def test_payment_pending_booking_is_confirmed(self):
        self.set_booking_status('payment_pending')
        self.post_webhook(self.event_payload())
        self.assert_booking('confirmed', 'paid')

    def test_duplicate_event_is_idempotent(self):
        payload = self.event_payload(event_id='evt_same')
        self.assertEqual(self.post_webhook(payload).status_code, 200)
        self.payment.refresh_from_db()
        first_updated = self.payment.updated_at

        second = self.post_webhook(payload)
        self.assertEqual(second.status_code, 200)  # acknowledged -> Stripe stops retrying
        self.assertTrue(second.data['duplicate'])
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.updated_at, first_updated)
        self.assertEqual(Payment.objects.filter(booking=self.booking).count(), 1)
        self.assert_booking('confirmed', 'paid')

    def test_second_completed_event_for_same_session_is_idempotent(self):
        self.post_webhook(self.event_payload(event_id='evt_a'))
        second = self.post_webhook(self.event_payload(event_id='evt_b'))
        self.assertTrue(second.data['duplicate'])
        self.assertEqual(Payment.objects.filter(booking=self.booking).count(), 1)

    def test_unpaid_completed_session_is_not_marked_paid(self):
        response = self.post_webhook(self.event_payload(payment_status='unpaid'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['booking_confirmed'])
        self.payment.refresh_from_db()
        self.assertNotEqual(self.payment.status, 'paid')
        self.assert_booking('pending', 'pending')

    def test_expired_session_is_not_paid_and_closes_attempt(self):
        response = self.post_webhook(self.event_payload(event_type='checkout.session.expired',
                                                        payment_status='unpaid'))
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'cancelled')
        self.assert_booking('pending', 'pending')

    def test_completed_after_expired_does_not_mark_paid(self):
        self.post_webhook(self.event_payload(event_type='checkout.session.expired', event_id='evt_x'))
        response = self.post_webhook(self.event_payload(event_id='evt_y'))
        self.assertTrue(response.data['duplicate'])
        self.assert_booking('pending', 'pending')

    def test_amount_mismatch_does_not_confirm_booking(self):
        response = self.post_webhook(self.event_payload(amount_total=100))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['requires_review'])
        self.payment.refresh_from_db()
        self.assertNotEqual(self.payment.status, 'paid')
        self.assertIn('expected 2310000', self.payment.error_message)
        self.assert_booking('pending', 'pending')

    def test_currency_mismatch_does_not_confirm_booking(self):
        response = self.post_webhook(self.event_payload(currency='usd'))
        self.assertTrue(response.data['requires_review'])
        self.assert_booking('pending', 'pending')

    def test_cancelled_booking_is_not_revived(self):
        BookingService.cancel_booking(self.booking)
        response = self.post_webhook(self.event_payload())

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['booking_confirmed'])
        self.assertTrue(response.data['requires_refund'])
        self.assert_booking('cancelled', 'pending')
        # The captured money is recorded (refundable), with the reason
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')
        self.assertEqual(self.payment.gateway_response['payment_intent'], self.PAYMENT_INTENT)
        self.assertIn('refund required', self.payment.error_message)
        # Rooms stay released
        _, available = BookingService.check_availability(
            self.room_type, self.booking.check_in_date, self.booking.check_out_date
        )
        self.assertEqual(available, self.room_type.total_rooms)

    def test_rejected_booking_is_not_revived(self):
        BookingService.owner_reject_booking(self.booking)
        response = self.post_webhook(self.event_payload())
        self.assertFalse(response.data['booking_confirmed'])
        self.assert_booking('rejected', 'pending')

    def test_unknown_session_is_acknowledged_without_changes(self):
        response = self.post_webhook(self.event_payload(id='cs_other_integration'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['matched'])
        self.assertEqual(Payment.objects.count(), 1)
        self.assert_booking('pending', 'pending')

    def test_unhandled_event_type_is_acknowledged_and_ignored(self):
        response = self.post_webhook(self.event_payload(event_type='customer.created'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['ignored'], 'customer.created')
        self.assert_booking('pending', 'pending')

    def test_offline_payment_reference_cannot_be_settled_by_stripe_event(self):
        offline = self.make_payment(method='pay_at_property', reference='cs_offline_ref')
        self.post_webhook(self.event_payload(id='cs_offline_ref'))
        offline.refresh_from_db()
        self.assertEqual(offline.status, 'pending')


# ---------------------------------------------------------------------------
# Payment confirmation email
# ---------------------------------------------------------------------------

class PaymentConfirmationEmailTestCase(StripeTestBase):

    def test_template_renders_with_payment_context(self):
        payment = self.make_payment(status='paid')
        NotificationService.send_payment_confirmation(self.booking, payment.amount, payment=payment)

        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn(self.booking.booking_reference, body)
        self.assertIn(self.property.name, body)
        self.assertIn('23100', body.replace(',', ''))
        self.assertIn('Pay at property', body)

    def test_template_renders_without_optional_payment(self):
        html = render_to_string('emails/payment_received.html', {
            'guest_name': 'Guest', 'booking_reference': 'SLB-1', 'amount': '100.00', 'currency': 'LKR',
        })
        self.assertIn('SLB-1', html)
        self.assertNotIn('Payment method', html)

    def test_successful_stripe_payment_sends_email_once(self):
        self.make_stripe_payment()
        payload = self.event_payload(event_id='evt_once')
        self.post_webhook(payload)
        self.post_webhook(payload)                                   # duplicate delivery
        self.post_webhook(self.event_payload(event_id='evt_other'))  # second event, same session
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Payment Received', mail.outbox[0].subject)

    def test_manual_offline_confirmation_sends_email_once(self):
        payment = self.make_payment()
        url = f'/api/payments/{payment.id}/confirm/'
        self.as_user(self.owner).post(url, {'status': 'paid'}, format='json')
        self.as_user(self.owner).post(url, {'status': 'paid'}, format='json')  # idempotent repeat
        self.assertEqual(len(mail.outbox), 1)

    def test_failed_confirmation_sends_no_email(self):
        payment = self.make_payment()
        self.as_user(self.owner).post(f'/api/payments/{payment.id}/confirm/', {'status': 'failed'}, format='json')
        self.assertEqual(len(mail.outbox), 0)

    def test_payment_is_saved_even_if_email_fails(self):
        payment = self.make_stripe_payment()
        with mock.patch.object(NotificationService, 'send_payment_confirmation', side_effect=RuntimeError('SMTP down')):
            response = self.post_webhook(self.event_payload())
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'paid')
        self.assert_booking('confirmed', 'paid')

    def test_manual_confirmation_is_saved_even_if_email_fails(self):
        payment = self.make_payment()
        with mock.patch.object(NotificationService, 'send_payment_confirmation', side_effect=RuntimeError('SMTP down')):
            response = self.as_user(self.owner).post(f'/api/payments/{payment.id}/confirm/', {'status': 'paid'}, format='json')
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'paid')


# ---------------------------------------------------------------------------
# Manual confirmation restrictions
# ---------------------------------------------------------------------------

class ManualStripeConfirmationTestCase(StripeTestBase):

    def test_owner_cannot_manually_confirm_stripe_payment(self):
        payment = self.make_stripe_payment()
        response = self.as_user(self.owner).post(f'/api/payments/{payment.id}/confirm/', {'status': 'paid'}, format='json')
        self.assertEqual(response.status_code, 403)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'pending')
        self.assert_booking('pending', 'pending')

    def test_admin_cannot_manually_confirm_stripe_payment(self):
        payment = self.make_stripe_payment()
        response = self.as_user(self.admin).post(f'/api/payments/{payment.id}/confirm/', {'status': 'paid'}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assert_booking('pending', 'pending')

    def test_owner_cannot_manually_fail_stripe_payment(self):
        payment = self.make_stripe_payment()
        response = self.as_user(self.owner).post(f'/api/payments/{payment.id}/confirm/', {'status': 'failed'}, format='json')
        self.assertEqual(response.status_code, 403)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'pending')

    def test_offline_confirmation_still_works(self):
        for method in ('pay_at_property', 'bank_transfer'):
            payment = self.make_payment(method=method)
            response = self.as_user(self.owner).post(f'/api/payments/{payment.id}/confirm/', {'status': 'paid'}, format='json')
            self.assertEqual(response.status_code, 200, response.data)
            payment.refresh_from_db()
            self.assertEqual(payment.status, 'paid')


# ---------------------------------------------------------------------------
# Stripe Checkout (server-side amount)
# ---------------------------------------------------------------------------

def fake_session(session_id='cs_test_new', url='https://checkout.stripe.com/c/pay/cs_test_new', expires_in=1800):
    return SimpleNamespace(id=session_id, url=url, expires_at=int(time.time()) + expires_in)


class StripeCheckoutTestCase(StripeTestBase):

    def initiate(self, **extra):
        return self.as_user(self.guest).post('/api/payments/initiate/', {
            'booking_id': str(self.booking.id), 'payment_method': 'stripe', **extra,
        }, format='json')

    @mock.patch('stripe.checkout.Session.create', return_value=fake_session())
    def test_checkout_amount_comes_from_server_side_booking_total(self, create):
        response = self.initiate(amount='1.00', total_price='1.00')  # fake client amounts
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['data']['payment_url'], 'https://checkout.stripe.com/c/pay/cs_test_new')

        kwargs = create.call_args.kwargs
        price = kwargs['line_items'][0]['price_data']
        self.assertEqual(price['unit_amount'], 2310000)  # LKR 23,100.00
        self.assertEqual(price['currency'], 'lkr')
        self.assertEqual(kwargs['line_items'][0]['quantity'], 1)
        self.assertEqual(kwargs['api_key'], TEST_API_KEY)
        self.assertEqual(kwargs['metadata']['booking_reference'], self.booking.booking_reference)

        payment = Payment.objects.get(booking=self.booking)
        self.assertEqual(payment.amount, self.booking.total_price)
        self.assertEqual(payment.transaction_reference, 'cs_test_new')
        self.assertEqual(kwargs['metadata']['payment_id'], str(payment.id))
        self.assertEqual(kwargs['idempotency_key'], f'checkout-{payment.id}')

    @mock.patch('stripe.checkout.Session.create', return_value=fake_session())
    def test_frontend_initiate_contract(self, create):
        """
        Exactly what frontend/src/lib/api.ts initiatePayment() sends and reads:
        request {booking_id, payment_method}; response {data: {payment_url, payment_id, ...}}.
        """
        response = self.as_user(self.guest).post('/api/payments/initiate/', {
            'booking_id': str(self.booking.id), 'payment_method': 'stripe',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data['data']
        for key in ('success', 'payment_id', 'payment_url', 'payment_method', 'amount', 'currency'):
            self.assertIn(key, data)
        self.assertTrue(data['payment_url'].startswith('https://'))
        self.assertEqual(data['payment_method'], 'stripe')

    def test_bookings_list_exposes_fields_used_by_pay_button(self):
        """/bookings decides Pay-button visibility from these server fields only."""
        response = self.as_user(self.guest).get('/api/bookings/')
        results = response.data.get('results', response.data)
        item = next(b for b in results if str(b['id']) == str(self.booking.id))
        for key in ('id', 'booking_reference', 'status', 'payment_status', 'total_price'):
            self.assertIn(key, item)

    @mock.patch('stripe.checkout.Session.create', return_value=fake_session())
    def test_checkout_redirects_to_existing_bookings_page(self, create):
        self.initiate()
        kwargs = create.call_args.kwargs
        self.assertTrue(kwargs['success_url'].startswith(f'{SITE}/bookings?payment=success'))
        self.assertTrue(kwargs['cancel_url'].startswith(f'{SITE}/bookings?payment=cancelled'))

    @mock.patch('stripe.checkout.Session.create', return_value=fake_session())
    def test_repeat_initiation_reuses_live_session(self, create):
        first = self.initiate()
        second = self.initiate()
        self.assertEqual(first.data['data']['payment_id'], second.data['data']['payment_id'])
        self.assertEqual(create.call_count, 1)
        self.assertEqual(Payment.objects.filter(booking=self.booking).count(), 1)

    def test_expired_session_is_replaced(self):
        with mock.patch('stripe.checkout.Session.create', return_value=fake_session('cs_old', expires_in=-10)):
            self.initiate()
        with mock.patch('stripe.checkout.Session.create', return_value=fake_session('cs_new')) as create:
            response = self.initiate()
        self.assertEqual(create.call_count, 1)
        self.assertEqual(Payment.objects.get(transaction_reference='cs_old').status, 'cancelled')
        self.assertEqual(Payment.objects.get(transaction_reference='cs_new').status, 'pending')
        self.assertEqual(response.data['data']['payment_url'], fake_session('cs_new').url)

    @mock.patch('stripe.checkout.Session.create', side_effect=stripe.APIConnectionError('network down'))
    def test_stripe_failure_saves_no_payment(self, create):
        response = self.initiate()
        self.assertEqual(response.status_code, 502)
        self.assertFalse(Payment.objects.filter(booking=self.booking).exists())

    @override_settings(STRIPE_LIVE_SECRET_KEY='')
    @mock.patch('stripe.checkout.Session.create')
    def test_unconfigured_stripe_is_refused(self, create):
        response = self.initiate()
        self.assertEqual(response.status_code, 502)
        create.assert_not_called()
        self.assertFalse(Payment.objects.filter(booking=self.booking).exists())

    @mock.patch('stripe.checkout.Session.create')
    def test_cancelled_booking_cannot_start_checkout(self, create):
        BookingService.cancel_booking(self.booking)
        self.assertEqual(self.initiate().status_code, 409)
        create.assert_not_called()

    @mock.patch('stripe.checkout.Session.create', return_value=fake_session())
    def test_other_guest_cannot_start_checkout(self, create):
        response = self.as_user(self.other_guest).post('/api/payments/initiate/', {
            'booking_id': str(self.booking.id), 'payment_method': 'stripe',
        }, format='json')
        self.assertEqual(response.status_code, 403)
        create.assert_not_called()


# ---------------------------------------------------------------------------
# Stripe refunds (real money path, mocked API)
# ---------------------------------------------------------------------------

def fake_refund(refund_id='re_test_1', status='succeeded'):
    return SimpleNamespace(id=refund_id, status=status)


class StripeRefundTestCase(StripeTestBase):

    def setUp(self):
        super().setUp()
        self.payment = self.make_stripe_payment(status='paid', payment_intent=self.PAYMENT_INTENT)

    def refund(self, amount=None, user=None):
        data = {} if amount is None else {'amount': amount}
        return self.as_user(user or self.owner).post(f'/api/payments/{self.payment.id}/refund/', data, format='json')

    @mock.patch('stripe.Refund.create', return_value=fake_refund())
    def test_refund_within_paid_amount_moves_money_via_stripe(self, create):
        response = self.refund('5000.00')
        self.assertEqual(response.status_code, 200, response.data)
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs['payment_intent'], self.PAYMENT_INTENT)
        self.assertEqual(kwargs['amount'], 500000)  # LKR 5,000.00
        self.assertEqual(kwargs['api_key'], TEST_API_KEY)
        refund = Refund.objects.get(payment=self.payment)
        self.assertEqual(refund.status, 'completed')
        self.assertEqual(response.data['data']['refund_reference'], 're_test_1')
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'partially_refunded')

    @mock.patch('stripe.Refund.create', return_value=fake_refund())
    def test_refund_above_paid_amount_is_rejected_before_stripe(self, create):
        response = self.refund('23100.01')
        self.assertEqual(response.status_code, 400)
        create.assert_not_called()
        self.assertFalse(Refund.objects.exists())

    @mock.patch('stripe.Refund.create', return_value=fake_refund())
    def test_cumulative_refunds_cannot_exceed_paid_amount(self, create):
        self.assertEqual(self.refund('20000.00').status_code, 200)
        self.assertEqual(self.refund('3100.01').status_code, 400)
        self.assertEqual(self.refund('3100.00').status_code, 200)
        self.assertEqual(create.call_count, 2)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'refunded')

    @mock.patch('stripe.Refund.create', return_value=fake_refund())
    def test_refund_idempotency_key_prevents_double_refund_on_retry(self, create):
        self.refund('1000.00')
        first_key = create.call_args.kwargs['idempotency_key']
        self.refund('1000.00')
        second_key = create.call_args.kwargs['idempotency_key']
        self.assertNotEqual(first_key, second_key)  # different logical refunds
        self.assertIn(str(self.payment.id), first_key)

    @mock.patch('stripe.Refund.create', return_value=fake_refund(status='pending'))
    def test_pending_stripe_refund_is_recorded_as_processing(self, create):
        self.refund('100.00')
        self.assertEqual(Refund.objects.get(payment=self.payment).status, 'processing')

    @mock.patch('stripe.Refund.create', side_effect=stripe.InvalidRequestError('charge already refunded', None))
    def test_stripe_error_records_nothing(self, create):
        response = self.refund('100.00')
        self.assertEqual(response.status_code, 502)
        self.assertFalse(Refund.objects.exists())
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')

    @mock.patch('stripe.Refund.create')
    def test_stripe_payment_without_payment_intent_cannot_be_refunded(self, create):
        self.payment.gateway_response = {'checkout_session_id': self.SESSION_ID}
        self.payment.save()
        self.assertEqual(self.refund('100.00').status_code, 400)
        create.assert_not_called()

    @mock.patch('stripe.Refund.create')
    def test_guest_and_other_owner_cannot_refund(self, create):
        self.assertEqual(self.refund('100.00', user=self.guest).status_code, 403)
        self.assertEqual(self.refund('100.00', user=self.other_owner).status_code, 403)
        create.assert_not_called()

    @mock.patch('stripe.Refund.create', return_value=fake_refund())
    def test_admin_can_refund_stripe_payment(self, create):
        self.assertEqual(self.refund('100.00', user=self.admin).status_code, 200)

    @mock.patch('stripe.Refund.create')
    def test_offline_refund_does_not_call_stripe(self, create):
        offline = self.make_payment(status='paid', method='pay_at_property')
        response = self.as_user(self.owner).post(f'/api/payments/{offline.id}/refund/', {'amount': '100.00'}, format='json')
        self.assertEqual(response.status_code, 200)
        create.assert_not_called()

    @mock.patch('stripe.Refund.create', return_value=fake_refund())
    def test_refund_after_webhook_uses_recorded_payment_intent(self, create):
        """End-to-end: webhook records the PaymentIntent, refund uses it."""
        self.payment.status = 'pending'
        self.payment.gateway_response = {'checkout_session_id': self.SESSION_ID}
        self.payment.save()
        self.post_webhook(self.event_payload(payment_intent='pi_from_webhook'))

        self.assertEqual(self.refund('100.00').status_code, 200)
        self.assertEqual(create.call_args.kwargs['payment_intent'], 'pi_from_webhook')
