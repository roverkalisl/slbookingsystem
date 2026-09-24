"""
Payment security / data-integrity regression tests:

- Stripe webhook: signature, booking-status guard, idempotency
- Refund limits: amount <= paid - already refunded, authorization
- Payment confirm: respects the requested outcome (paid / failed / cancelled)
- Payment initiation: only for active, unpaid bookings; no duplicate records
- Payment records are read-only through the generic API
- Malformed / unknown booking and payment ids return 404, not 500

Lives in the bookings app so it runs with the booking suite (the payments
app's own tests are stale and tracked separately).

Run with: python manage.py test apps.bookings.tests_payment_security
"""

import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Role, UserRole
from apps.payments.models import Payment, Refund
from apps.properties.models import Property, PropertyType, RoomType, Pricing
from .models import Booking
from .service import BookingService
from .tests import MultiRoomTestMixin, _next_weekday

User = get_user_model()


class PaymentTestBase(MultiRoomTestMixin, TestCase):
    """Guest books 1 room x 2 nights at owner's property (total 23,100)."""

    def setUp(self):
        self.make_fixture()
        self.booking = self.book(_next_weekday(0), nights=2, num_rooms=1)
        self.admin = User.objects.create_user(email='pay-admin@example.com', password='test', is_staff=True)

        owner_role = Role.objects.get(name='property_owner')
        guest_role = Role.objects.get(name='guest')
        self.other_owner = User.objects.create_user(email='pay-owner-b@example.com', password='test')
        UserRole.objects.create(user=self.other_owner, role=owner_role)
        self.other_guest = User.objects.create_user(email='pay-guest-b@example.com', password='test')
        UserRole.objects.create(user=self.other_guest, role=guest_role)

        self.client = APIClient()

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return self.client

    def make_payment(self, status='pending', method='pay_at_property', reference=None, amount=None):
        return Payment.objects.create(
            booking=self.booking,
            amount=amount if amount is not None else self.booking.total_price,
            status=status,
            payment_method=method,
            gateway_name=method,
            transaction_reference=reference or f'ref-{uuid.uuid4()}',
        )

    def set_booking_status(self, status):
        Booking.objects.filter(id=self.booking.id).update(status=status)
        self.booking.refresh_from_db()


# Stripe webhook / Checkout / refund tests live in tests_stripe.py (official
# SDK signature scheme, mocked Stripe API).


# ---------------------------------------------------------------------------
# Priority 2 - Refund limits
# ---------------------------------------------------------------------------

class RefundLimitTestCase(PaymentTestBase):

    def setUp(self):
        super().setUp()
        self.payment = self.make_payment(status='paid', amount=Decimal('10000.00'))

    def refund(self, amount=None, user=None):
        data = {} if amount is None else {'amount': amount}
        return self.as_user(user or self.owner).post(f'/api/payments/{self.payment.id}/refund/', data, format='json')

    def refunded_total(self):
        return sum((r.amount for r in Refund.objects.filter(payment=self.payment)), Decimal('0'))

    def test_refund_within_paid_amount_is_allowed(self):
        response = self.refund('4000.00')
        self.assertEqual(response.status_code, 200, response.data)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'partially_refunded')
        self.assertEqual(self.refunded_total(), Decimal('4000.00'))

    def test_refund_above_paid_amount_is_rejected(self):
        response = self.refund('10000.01')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Refund.objects.count(), 0)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')

    def test_two_partial_refunds_within_total_are_allowed(self):
        self.assertEqual(self.refund('4000.00').status_code, 200)
        self.assertEqual(self.refund('6000.00').status_code, 200)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'refunded')
        self.assertEqual(self.refunded_total(), Decimal('10000.00'))

    def test_cumulative_refund_above_paid_amount_is_rejected(self):
        self.assertEqual(self.refund('6000.00').status_code, 200)
        response = self.refund('5000.00')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.refunded_total(), Decimal('6000.00'))

    def test_zero_refund_is_rejected(self):
        self.assertEqual(self.refund('0').status_code, 400)
        self.assertEqual(Refund.objects.count(), 0)

    def test_negative_refund_is_rejected(self):
        self.assertEqual(self.refund('-500.00').status_code, 400)
        self.assertEqual(Refund.objects.count(), 0)

    def test_omitted_amount_refunds_remaining_balance_only(self):
        self.refund('3000.00')
        response = self.refund()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Decimal(str(response.data['data']['amount'])), Decimal('7000.00'))
        self.assertEqual(self.refunded_total(), Decimal('10000.00'))

    def test_fully_refunded_payment_cannot_be_refunded_again(self):
        self.refund('10000.00')
        self.assertEqual(self.refund('1.00').status_code, 400)

    def test_unpaid_payment_cannot_be_refunded(self):
        pending = self.make_payment(status='pending')
        response = self.as_user(self.owner).post(f'/api/payments/{pending.id}/refund/', {'amount': '100.00'}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_refund_on_cancelled_booking_is_allowed(self):
        """Refunds are exactly what a cancelled, paid booking needs."""
        BookingService.cancel_booking(self.booking)
        self.assertEqual(self.refund('10000.00').status_code, 200)

    def test_other_owner_cannot_refund(self):
        self.assertEqual(self.refund('100.00', user=self.other_owner).status_code, 403)
        self.assertEqual(Refund.objects.count(), 0)

    def test_guest_cannot_refund_own_payment(self):
        self.assertEqual(self.refund('100.00', user=self.guest).status_code, 403)
        self.assertEqual(Refund.objects.count(), 0)

    def test_admin_refund_still_works_and_is_capped(self):
        self.assertEqual(self.refund('2500.00', user=self.admin).status_code, 200)
        self.assertEqual(self.refund('7500.01', user=self.admin).status_code, 400)
        self.assertEqual(self.refunded_total(), Decimal('2500.00'))


# ---------------------------------------------------------------------------
# Priority 3 - Payment confirm respects the requested outcome
# ---------------------------------------------------------------------------

class PaymentConfirmStatusTestCase(PaymentTestBase):

    def setUp(self):
        super().setUp()
        self.payment = self.make_payment()

    def confirm(self, outcome, user=None):
        return self.as_user(user or self.owner).post(
            f'/api/payments/{self.payment.id}/confirm/',
            {'status': outcome, 'transaction_reference': 'TXN-1'}, format='json'
        )

    def assert_state(self, payment_status, booking_status, booking_payment_status):
        self.payment.refresh_from_db()
        self.booking.refresh_from_db()
        self.assertEqual(self.payment.status, payment_status)
        self.assertEqual(self.booking.status, booking_status)
        self.assertEqual(self.booking.payment_status, booking_payment_status)

    def test_confirm_paid(self):
        response = self.confirm('paid')
        self.assertEqual(response.status_code, 200, response.data)
        self.assert_state('paid', 'confirmed', 'paid')

    def test_confirm_failed_does_not_mark_paid_or_confirm_booking(self):
        response = self.confirm('failed')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['data']['status'], 'failed')
        self.assert_state('failed', 'pending', 'failed')

    def test_confirm_cancelled_does_not_confirm_booking(self):
        self.assertEqual(self.confirm('cancelled').status_code, 200)
        self.assert_state('cancelled', 'pending', 'cancelled')

    def test_failed_payment_cannot_later_be_marked_paid(self):
        self.confirm('failed')
        self.assertEqual(self.confirm('paid').status_code, 409)
        self.assert_state('failed', 'pending', 'failed')

    def test_paid_payment_cannot_be_marked_failed(self):
        self.confirm('paid')
        self.assertEqual(self.confirm('failed').status_code, 409)
        self.assert_state('paid', 'confirmed', 'paid')

    def test_repeated_paid_confirmation_is_idempotent(self):
        self.confirm('paid')
        response = self.confirm('paid')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Payment already confirmed')
        self.assert_state('paid', 'confirmed', 'paid')

    def test_invalid_outcome_is_rejected(self):
        self.assertEqual(self.confirm('refunded').status_code, 400)
        self.assert_state('pending', 'pending', 'pending')

    def test_guest_is_still_blocked(self):
        self.assertEqual(self.confirm('paid', user=self.guest).status_code, 403)
        self.assert_state('pending', 'pending', 'pending')

    def test_other_owner_is_blocked(self):
        self.assertEqual(self.confirm('paid', user=self.other_owner).status_code, 403)

    def test_cancelled_booking_cannot_be_revived(self):
        BookingService.cancel_booking(self.booking)
        self.assertEqual(self.confirm('paid').status_code, 409)
        self.assert_state('pending', 'cancelled', 'pending')

    def test_rejected_booking_cannot_be_revived(self):
        BookingService.owner_reject_booking(self.booking)
        self.assertEqual(self.confirm('paid').status_code, 409)
        self.assert_state('pending', 'rejected', 'pending')


# ---------------------------------------------------------------------------
# Priority 4 - Payment initiation
# ---------------------------------------------------------------------------

class PaymentInitiationTestCase(PaymentTestBase):

    def initiate(self, method='pay_at_property', user=None, booking=None):
        return self.as_user(user or self.guest).post('/api/payments/initiate/', {
            'booking_id': str((booking or self.booking).id),
            'payment_method': method,
        }, format='json')

    def test_pending_booking_can_start_payment_with_server_amount(self):
        response = self.initiate()
        self.assertEqual(response.status_code, 200, response.data)
        payment = Payment.objects.get(booking=self.booking)
        self.assertEqual(payment.amount, self.booking.total_price)
        self.assertEqual(payment.status, 'pending')

    def test_payment_pending_booking_can_start_payment(self):
        self.set_booking_status('payment_pending')
        self.assertEqual(self.initiate().status_code, 200)

    def test_client_supplied_amount_is_ignored(self):
        self.as_user(self.guest).post('/api/payments/initiate/', {
            'booking_id': str(self.booking.id), 'payment_method': 'pay_at_property', 'amount': '1.00',
        }, format='json')
        self.assertEqual(Payment.objects.get(booking=self.booking).amount, self.booking.total_price)

    def test_repeated_initiation_reuses_open_payment(self):
        first = self.initiate()
        second = self.initiate()
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(first.data['data']['payment_id'], second.data['data']['payment_id'])
        self.assertEqual(Payment.objects.filter(booking=self.booking).count(), 1)

    def test_other_methods_still_initiate(self):
        # Stripe initiation (real Checkout Session) is covered with a mocked
        # Stripe API in tests_stripe.py.
        self.assertEqual(self.initiate(method='bank_transfer').status_code, 200)

    def test_cancelled_booking_cannot_start_payment(self):
        BookingService.cancel_booking(self.booking)
        self.assertEqual(self.initiate().status_code, 409)
        self.assertFalse(Payment.objects.filter(booking=self.booking).exists())

    def test_rejected_booking_cannot_start_payment(self):
        BookingService.owner_reject_booking(self.booking)
        self.assertEqual(self.initiate().status_code, 409)
        self.assertFalse(Payment.objects.filter(booking=self.booking).exists())

    def test_already_paid_booking_cannot_start_another_payment(self):
        payment = self.make_payment()
        from apps.payments.service import PaymentService
        PaymentService.confirm_payment(payment)
        self.assertEqual(self.initiate(method='bank_transfer').status_code, 409)
        self.assertEqual(Payment.objects.filter(booking=self.booking).count(), 1)

    def test_other_guest_cannot_start_payment(self):
        self.assertEqual(self.initiate(user=self.other_guest).status_code, 403)


# ---------------------------------------------------------------------------
# Payment records are read-only; isolation
# ---------------------------------------------------------------------------

class PaymentRecordProtectionTestCase(PaymentTestBase):

    def setUp(self):
        super().setUp()
        self.payment = self.make_payment(status='paid')

    def test_guest_cannot_delete_own_payment(self):
        response = self.as_user(self.guest).delete(f'/api/payments/{self.payment.id}/')
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Payment.objects.filter(id=self.payment.id).exists())

    def test_owner_cannot_delete_payment(self):
        response = self.as_user(self.owner).delete(f'/api/payments/{self.payment.id}/')
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Payment.objects.filter(id=self.payment.id).exists())

    def test_nobody_can_edit_payment_amount_or_status(self):
        for user in (self.guest, self.owner, self.admin):
            response = self.as_user(user).patch(
                f'/api/payments/{self.payment.id}/', {'amount': '1.00', 'status': 'refunded'}, format='json'
            )
            self.assertEqual(response.status_code, 405)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.amount, self.booking.total_price)
        self.assertEqual(self.payment.status, 'paid')

    def test_payments_cannot_be_created_through_generic_route(self):
        response = self.as_user(self.guest).post('/api/payments/', {
            'booking': str(self.booking.id), 'amount': '1.00', 'status': 'paid', 'payment_method': 'stripe',
        }, format='json')
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Payment.objects.count(), 1)

    def test_other_guest_cannot_see_payment(self):
        response = self.as_user(self.other_guest).get(f'/api/payments/{self.payment.id}/')
        self.assertEqual(response.status_code, 404)

    def test_other_owner_cannot_see_payment(self):
        response = self.as_user(self.other_owner).get(f'/api/payments/{self.payment.id}/')
        self.assertEqual(response.status_code, 404)

    def test_guest_and_owner_can_see_their_payment(self):
        self.assertEqual(self.as_user(self.guest).get(f'/api/payments/{self.payment.id}/').status_code, 200)
        self.assertEqual(self.as_user(self.owner).get(f'/api/payments/{self.payment.id}/').status_code, 200)


# ---------------------------------------------------------------------------
# Priority 5 - Invalid ids
# ---------------------------------------------------------------------------

class InvalidIdTestCase(PaymentTestBase):
    MALFORMED = 'not-a-valid-uuid'

    def assert_404_for_bad_ids(self, method, url_template, user, data=None):
        client = self.as_user(user)
        for bad_id in (self.MALFORMED, str(uuid.uuid4())):
            response = getattr(client, method)(url_template.format(bad_id), data or {}, format='json')
            self.assertEqual(response.status_code, 404, f'{url_template.format(bad_id)} -> {response.status_code}')

    def test_invalid_cancel_id(self):
        self.assert_404_for_bad_ids('post', '/api/bookings/{}/cancel/', self.guest)

    def test_invalid_confirm_id(self):
        self.assert_404_for_bad_ids('post', '/api/bookings/{}/confirm/', self.owner)

    def test_invalid_reject_id(self):
        self.assert_404_for_bad_ids('post', '/api/bookings/{}/reject/', self.owner)

    def test_invalid_confirm_payment_id(self):
        self.assert_404_for_bad_ids('post', '/api/bookings/{}/confirm_payment/', self.owner)

    def test_invalid_booking_detail_id(self):
        self.assert_404_for_bad_ids('get', '/api/bookings/{}/', self.guest)

    def test_invalid_payment_confirm_and_refund_ids(self):
        self.assert_404_for_bad_ids('post', '/api/payments/{}/confirm/', self.owner, {'status': 'paid'})
        self.assert_404_for_bad_ids('post', '/api/payments/{}/refund/', self.owner, {'amount': '1.00'})

    def test_valid_ids_still_work(self):
        response = self.as_user(self.owner).post(f'/api/bookings/{self.booking.id}/confirm/')
        self.assertEqual(response.status_code, 200)
