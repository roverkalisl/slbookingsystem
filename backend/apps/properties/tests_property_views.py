"""
Public property view tracking (POST /api/properties/{id}/view/) and the admin
dashboard view statistics.

One view per property, per visitor (HMAC of IP + browser + day), per day;
owners, admins and non-approved properties are never counted.

Run with: python manage.py test apps.properties.tests_property_views
"""

import threading
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.core.models import Role, UserRole
from .models import Property, PropertyType, PropertyView
from .view_tracking import client_ip, record_property_view, visitor_fingerprint

User = get_user_model()
UA_CHROME = 'Mozilla/5.0 (Windows NT 10.0) Chrome/126.0'
UA_FIREFOX = 'Mozilla/5.0 (X11; Linux x86_64) Firefox/127.0'


def make_property(owner, name, status='approved', city='Galle'):
    ptype, _ = PropertyType.objects.get_or_create(name='Views Hotel')
    return Property.objects.create(owner=owner, property_type=ptype, name=name, description='d',
                                   city=city, district='Galle', province='Southern', status=status)


class PropertyViewEndpointTestCase(APITestCase):
    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        guest_role, _ = Role.objects.get_or_create(name='guest')
        self.owner = User.objects.create_user(email='views-owner@example.com', password='x')
        UserRole.objects.create(user=self.owner, role=owner_role)
        self.guest = User.objects.create_user(email='views-guest@example.com', password='x')
        UserRole.objects.create(user=self.guest, role=guest_role)
        self.admin = User.objects.create_superuser(email='views-admin@example.com', password='x')
        self.approved = make_property(self.owner, 'Viewed Villa')
        self.draft = make_property(self.owner, 'Draft Villa', status='draft')

    def view(self, prop_id, ua=UA_CHROME, ip='203.0.113.10', **extra):
        return self.client.post(f'/api/properties/{prop_id}/view/', REMOTE_ADDR=ip, HTTP_USER_AGENT=ua, **extra)

    def test_anonymous_view_of_approved_property_is_counted(self):
        response = self.view(self.approved.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'success': True, 'counted': True})
        row = PropertyView.objects.get()
        self.assertEqual(row.property, self.approved)
        self.assertEqual(row.viewed_on, timezone.localdate())

    def test_same_visitor_same_day_counted_once(self):
        for _ in range(5):
            self.view(self.approved.id)
        self.assertEqual(PropertyView.objects.count(), 1)
        self.assertEqual(self.view(self.approved.id).data['counted'], False)

    def test_different_visitors_are_counted_separately(self):
        self.view(self.approved.id, ua=UA_CHROME, ip='203.0.113.10')
        self.view(self.approved.id, ua=UA_FIREFOX, ip='203.0.113.10')
        self.view(self.approved.id, ua=UA_CHROME, ip='198.51.100.7')
        self.assertEqual(PropertyView.objects.count(), 3)

    def test_logged_in_guest_is_counted(self):
        self.client.force_authenticate(self.guest)
        self.assertTrue(self.view(self.approved.id).data['counted'])

    def test_owner_view_is_not_counted(self):
        self.client.force_authenticate(self.owner)
        response = self.view(self.approved.id)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['counted'])
        self.assertFalse(PropertyView.objects.exists())

    def test_admin_view_is_not_counted(self):
        self.client.force_authenticate(self.admin)
        self.assertFalse(self.view(self.approved.id).data['counted'])
        staff = User.objects.create_user(email='views-staff@example.com', password='x', is_staff=True)
        self.client.force_authenticate(staff)
        self.assertFalse(self.view(self.approved.id).data['counted'])
        self.assertFalse(PropertyView.objects.exists())

    def test_unapproved_missing_or_malformed_property_is_not_counted(self):
        for status in ('draft', 'pending_approval', 'rejected', 'suspended', 'unpublished'):
            Property.objects.filter(pk=self.draft.pk).update(status=status)
            self.assertEqual(self.view(self.draft.id).status_code, 404, status)
        self.assertEqual(self.view('3f2c7a9e-1b2d-4c5e-8f90-123456789abc').status_code, 404)
        self.assertEqual(self.view('not-a-uuid').status_code, 404)
        self.assertFalse(PropertyView.objects.exists())

    def test_reading_property_or_searching_does_not_count(self):
        self.client.get(f'/api/properties/{self.approved.id}/')
        self.client.get('/api/properties/search/advanced/')
        self.client.force_authenticate(self.owner)
        self.client.get(f'/api/properties/{self.approved.id}/manage/')
        self.assertFalse(PropertyView.objects.exists())

    def test_no_raw_ip_or_identity_is_stored(self):
        self.client.force_authenticate(self.guest)
        self.view(self.approved.id, ip='203.0.113.99')
        row = PropertyView.objects.get()
        self.assertEqual(len(row.visitor_hash), 64)
        for secret in ('203.0.113.99', str(self.guest.id), self.guest.email, 'Chrome'):
            self.assertNotIn(secret, row.visitor_hash)

    def test_forwarded_for_uses_the_proxy_appended_address(self):
        # A client-supplied first entry cannot create a new visitor
        self.view(self.approved.id, HTTP_X_FORWARDED_FOR='1.1.1.1, 203.0.113.50')
        self.view(self.approved.id, HTTP_X_FORWARDED_FOR='9.9.9.9, 203.0.113.50')
        self.assertEqual(PropertyView.objects.count(), 1)


class VisitorFingerprintTestCase(TestCase):
    def request(self, ip='203.0.113.10', ua=UA_CHROME, forwarded=None):
        extra = {'REMOTE_ADDR': ip, 'HTTP_USER_AGENT': ua}
        if forwarded:
            extra['HTTP_X_FORWARDED_FOR'] = forwarded
        return RequestFactory().post('/', **extra)

    def test_fingerprint_is_stable_per_day_and_changes_daily(self):
        today = timezone.localdate()
        self.assertEqual(visitor_fingerprint(self.request(), today), visitor_fingerprint(self.request(), today))
        self.assertNotEqual(visitor_fingerprint(self.request(), today),
                            visitor_fingerprint(self.request(), today + timedelta(days=1)))
        self.assertNotEqual(visitor_fingerprint(self.request(ua=UA_CHROME), today),
                            visitor_fingerprint(self.request(ua=UA_FIREFOX), today))

    def test_client_ip(self):
        self.assertEqual(client_ip(self.request(ip='10.0.0.5')), '10.0.0.5')
        self.assertEqual(client_ip(self.request(forwarded='1.2.3.4, 203.0.113.9')), '203.0.113.9')

    def test_database_rejects_a_duplicate_daily_view(self):
        owner = User.objects.create_user(email='fp-owner@example.com', password='x')
        prop = make_property(owner, 'Constraint Villa')
        PropertyView.objects.create(property=prop, viewed_on=timezone.localdate(), visitor_hash='a' * 64)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PropertyView.objects.create(property=prop, viewed_on=timezone.localdate(), visitor_hash='a' * 64)


class ConcurrentPropertyViewTestCase(TransactionTestCase):
    """
    Simultaneous requests from one visitor must still produce ONE row.

    SQLite-only note (same as the booking concurrency tests): the shared
    in-memory test database can answer concurrent writers with SQLITE_LOCKED
    ("database table is locked"), which PostgreSQL never does. Those lock
    errors are retried here and never counted as a result; on PostgreSQL an
    OperationalError is re-raised as a real failure.
    """
    MAX_LOCK_RETRIES = 20

    def test_concurrent_duplicate_views_create_one_row(self):
        import random
        import time
        from django.contrib.auth.models import AnonymousUser
        from django.db.utils import OperationalError

        owner = User.objects.create_user(email='conc-owner@example.com', password='x')
        prop = make_property(owner, 'Busy Villa')
        results, errors = [], []
        barrier = threading.Barrier(6)

        def worker():
            try:
                request = RequestFactory().post('/', REMOTE_ADDR='203.0.113.77', HTTP_USER_AGENT=UA_CHROME)
                request.user = AnonymousUser()
                barrier.wait(timeout=10)
                for attempt in range(self.MAX_LOCK_RETRIES):
                    try:
                        results.append(record_property_view(prop, request))
                        return
                    except OperationalError as exc:
                        if connection.vendor != 'sqlite' or attempt == self.MAX_LOCK_RETRIES - 1:
                            raise
                        time.sleep(random.uniform(0.01, 0.05))
            except Exception as exc:  # reported below
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 6)  # every request got a real answer
        self.assertEqual(PropertyView.objects.filter(property=prop).count(), 1)
        self.assertEqual(results.count(True), 1)


class AdminViewStatisticsTestCase(APITestCase):
    URL = '/api/admin/stats/dashboard/'

    def setUp(self):
        self.admin = User.objects.create_superuser(email='stats-admin@example.com', password='x')
        owner = User.objects.create_user(email='stats-owner@example.com', password='x')
        self.top = make_property(owner, 'Top Villa', city='Ella')
        self.second = make_property(owner, 'Second Villa', city='Kandy')
        self.unviewed = make_property(owner, 'Quiet Villa')
        self.hidden = make_property(owner, 'Suspended Villa', status='suspended')

        today = timezone.localdate()
        month_start = today.replace(day=1)
        last_month = month_start - timedelta(days=1)
        rows = [
            (self.top, today, 3), (self.top, month_start, 2), (self.top, last_month, 1),
            (self.second, today, 1), (self.second, last_month, 1),
            (self.hidden, today, 10),  # views of a no-longer-public property
        ]
        seq = 0
        for prop, day, count in rows:
            for _ in range(count):
                seq += 1
                PropertyView.objects.create(property=prop, viewed_on=day, visitor_hash=f'{seq:064d}')
        # month_start may be today (on the 1st) - expected values follow the same rule
        self.expected_today = 3 + 1 + 10 + (2 if month_start == today else 0)
        self.expected_month = 3 + 2 + 1 + 10

    def stats(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        return response.data['data']

    def test_view_totals(self):
        data = self.stats()
        self.assertEqual(data['total_property_views'], 18)  # 3+2+1 + 1+1 + 10
        self.assertEqual(data['property_views_today'], self.expected_today)
        self.assertEqual(data['property_views_this_month'], self.expected_month)

    def test_most_viewed_lists_only_approved_properties_in_order(self):
        rows = self.stats()['most_viewed_properties']
        self.assertEqual([row['name'] for row in rows], ['Top Villa', 'Second Villa'])
        self.assertEqual(rows[0], {'id': str(self.top.id), 'name': 'Top Villa', 'city': 'Ella', 'view_count': 6})
        self.assertEqual(rows[1]['view_count'], 2)
        self.assertNotIn('Suspended Villa', [row['name'] for row in rows])
        self.assertNotIn('Quiet Villa', [row['name'] for row in rows])

    def test_non_admin_cannot_read_stats(self):
        owner = User.objects.get(email='stats-owner@example.com')
        self.client.force_authenticate(owner)
        self.assertIn(self.client.get(self.URL).status_code, (401, 403))
