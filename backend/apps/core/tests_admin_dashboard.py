"""
Super Admin dashboard statistics - regression tests for the production
outage where GET /api/admin/stats/dashboard/ returned HTTP 500
("relation property_views does not exist": migration 0008 was committed but
never applied, because the Render preDeployCommand does not run) and the
dashboard showed every statistic as 0.

- the property_views table comes from migration 0008 and all migrations apply
- start.sh applies migrations before starting the web server
- a superuser gets real, non-zero platform-wide statistics
- admins are treated as admins even if they also hold owner/guest roles

Run with: python manage.py test apps.core.tests_admin_dashboard
"""

import os
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.bookings.models import Booking
from apps.core.models import Role, User, UserRole
from apps.payments.models import Payment
from apps.properties.models import Property, PropertyType, PropertyView, RoomType

URL = '/api/admin/stats/dashboard/'


class PropertyViewsMigrationTestCase(TestCase):
    def test_property_views_table_is_created_by_migration_0008(self):
        loader = MigrationLoader(connection)
        migration = loader.disk_migrations[('properties', '0008_property_views')]
        created = [op.name for op in migration.operations if op.__class__.__name__ == 'CreateModel']
        self.assertEqual(created, ['PropertyView'])
        self.assertEqual(PropertyView._meta.db_table, 'property_views')
        # The test database is built by running the migrations - the table must exist
        self.assertIn('property_views', connection.introspection.table_names())

    def test_no_unapplied_or_missing_migrations(self):
        executor = MigrationExecutor(connection)
        self.assertEqual(executor.migration_plan(executor.loader.graph.leaf_nodes()), [])
        # Models and migrations agree - no migration is missing from the repo
        call_command('makemigrations', check=True, dry_run=True, stdout=StringIO())


class StartScriptMigratesTestCase(SimpleTestCase):
    """Render ignores Procfile 'release:' and this service's preDeployCommand
    does not run, so start.sh must apply migrations before gunicorn."""

    def test_start_script_runs_migrate_before_gunicorn(self):
        path = os.path.join(settings.BASE_DIR, 'start.sh')
        with open(path, 'rb') as f:
            raw = f.read()
        self.assertNotIn(b'\r\n', raw, 'start.sh must use LF line endings for bash')
        lines = [line.strip() for line in raw.decode().splitlines() if line.strip() and not line.strip().startswith('#')]
        self.assertIn('set -e', lines)
        migrate = next(i for i, line in enumerate(lines) if 'manage.py migrate' in line)
        seed = next(i for i, line in enumerate(lines) if 'manage.py seed_master_data' in line)
        gunicorn = next(i for i, line in enumerate(lines) if 'gunicorn' in line)
        self.assertLess(lines.index('set -e'), migrate)
        self.assertLess(migrate, seed)
        self.assertLess(seed, gunicorn)
        # A failed migration must stop startup (plain command under set -e)...
        self.assertEqual(lines[migrate], 'python manage.py migrate --noinput')
        # ...while a failed seed only warns (master data is not needed to serve requests)
        self.assertIn('||', lines[seed])


class AdminDashboardStatisticsTestCase(APITestCase):
    def setUp(self):
        self.owner_role, _ = Role.objects.get_or_create(name='property_owner')
        self.guest_role, _ = Role.objects.get_or_create(name='guest')
        self.admin = User.objects.create_superuser(email='dash-admin@example.com', password='x')

        self.owner = self.user('dash-owner@example.com', self.owner_role)
        self.guest = self.user('dash-guest@example.com', self.guest_role)
        ptype = PropertyType.objects.create(name='Dash Hotel')
        make = lambda name, status: Property.objects.create(
            owner=self.owner, property_type=ptype, name=name, description='d',
            city='Galle', district='Galle', province='Southern', status=status, average_rating=Decimal('4.50'))
        self.approved = make('Approved One', 'approved')
        make('Approved Two', 'approved')
        make('Pending One', 'pending_approval')
        make('Draft One', 'draft')
        room = RoomType.objects.create(property=self.approved, name='Room', max_adults=2, total_occupancy=2, total_rooms=5)

        check_in = date.today() + timedelta(days=10)
        def book(ref, status):
            return Booking.objects.create(
                booking_reference=ref, property=self.approved, room_type=room, guest=self.guest,
                check_in_date=check_in, check_out_date=check_in + timedelta(days=2), number_of_nights=2,
                number_of_adults=2, room_price=Decimal('10000'), subtotal=Decimal('20000'),
                total_price=Decimal('20000'), status=status)
        paid = book('DASH-1', 'confirmed')
        book('DASH-2', 'pending')
        Payment.objects.create(booking=paid, amount=Decimal('20000.00'), status='paid', payment_method='stripe')
        PropertyView.objects.create(property=self.approved, viewed_on=timezone.localdate(), visitor_hash='a' * 64)

    def user(self, email, role):
        user = User.objects.create_user(email=email, password='x')
        UserRole.objects.create(user=user, role=role)
        return user

    def test_superuser_gets_real_non_zero_statistics(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200, response.content)
        data = response.data['data']
        self.assertEqual(data['total_users'], 3)
        self.assertEqual(data['total_owners'], 1)
        self.assertEqual(data['total_guests'], 1)
        self.assertEqual(data['total_properties'], 4)
        self.assertEqual(data['pending_properties'], 1)
        self.assertEqual(data['approved_properties'], 2)
        self.assertEqual(data['total_bookings'], 2)
        self.assertEqual(data['confirmed_bookings'], 1)
        self.assertEqual(data['pending_bookings'], 1)
        self.assertEqual(Decimal(data['platform_revenue']), Decimal('20000.00'))
        self.assertEqual(Decimal(data['average_rating']), Decimal('4.50'))
        self.assertEqual(data['total_property_views'], 1)
        self.assertEqual(data['property_views_today'], 1)
        self.assertEqual(data['property_views_this_month'], 1)
        self.assertEqual(data['most_viewed_properties'][0]['id'], str(self.approved.id))

    def test_admin_with_extra_roles_still_gets_statistics(self):
        for role in (self.owner_role, self.guest_role):
            UserRole.objects.get_or_create(user=self.admin, role=role)
        self.client.force_authenticate(self.admin)
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['total_properties'], 4)

    def test_non_admins_are_refused(self):
        for user in (self.owner, self.guest):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(URL).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(URL).status_code, 401)


class AdminRolePriorityTestCase(APITestCase):
    """An admin who ALSO holds an owner or guest role is scoped as an admin."""

    def setUp(self):
        owner_role, _ = Role.objects.get_or_create(name='property_owner')
        guest_role, _ = Role.objects.get_or_create(name='guest')
        super_admin_role, _ = Role.objects.get_or_create(name='super_admin')
        owner = User.objects.create_user(email='prio-owner@example.com', password='x')
        UserRole.objects.create(user=owner, role=owner_role)
        ptype = PropertyType.objects.create(name='Prio Hotel')
        make = lambda name, status: Property.objects.create(
            owner=owner, property_type=ptype, name=name, description='d',
            city='Galle', district='Galle', province='Southern', status=status)
        self.all_ids = {str(make(n, s).id) for n, s in
                        (('P approved', 'approved'), ('P pending', 'pending_approval'), ('P draft', 'draft'))}
        self.draft_room = RoomType.objects.create(property=Property.objects.get(name='P draft'), name='Draft room',
                                                  max_adults=2, total_occupancy=2, total_rooms=1)

        self.staff_owner = User.objects.create_user(email='prio-staff-owner@example.com', password='x', is_staff=True)
        UserRole.objects.create(user=self.staff_owner, role=owner_role)
        self.superuser_guest = User.objects.create_superuser(email='prio-super-guest@example.com', password='x')
        UserRole.objects.create(user=self.superuser_guest, role=guest_role)
        self.role_admin_owner = User.objects.create_user(email='prio-role-admin@example.com', password='x')
        UserRole.objects.create(user=self.role_admin_owner, role=super_admin_role)
        UserRole.objects.create(user=self.role_admin_owner, role=owner_role)
        self.plain_owner = owner

    def ids(self, user, url='/api/properties/'):
        self.client.force_authenticate(user)
        data = self.client.get(url).data
        rows = data.get('results', data) if isinstance(data, dict) else data
        return {row['id'] for row in rows}

    def test_admin_with_owner_or_guest_role_sees_all_properties(self):
        for admin in (self.staff_owner, self.superuser_guest, self.role_admin_owner):
            self.assertEqual(self.ids(admin), self.all_ids, admin.email)
            self.assertEqual(self.ids(admin, '/api/properties/?status=pending_approval'),
                             {i for i in self.all_ids if Property.objects.get(pk=i).status == 'pending_approval'})

    def test_admin_with_owner_role_sees_other_owners_draft_rooms(self):
        self.client.force_authenticate(self.staff_owner)
        self.assertEqual(self.client.get(f'/api/properties/rooms/{self.draft_room.id}/').status_code, 200)

    def test_plain_owner_scope_is_unchanged(self):
        self.assertEqual(self.ids(self.plain_owner), self.all_ids)  # all three are this owner's own
        other = User.objects.create_user(email='prio-other-owner@example.com', password='x')
        UserRole.objects.create(user=other, role=Role.objects.get(name='property_owner'))
        self.assertEqual(self.ids(other), set())
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(f'/api/properties/rooms/{self.draft_room.id}/').status_code, 404)
