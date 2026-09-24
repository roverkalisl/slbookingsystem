"""
Tests for serving the Next.js static export (config/urls.py resolve_frontend_html).

Dynamic [id] routes are pre-rendered once with the placeholder id '0'; every
real id must be served that shell, never the home page.

Run with: python manage.py test config.tests_frontend_routing
"""

import os
import tempfile

from django.test import SimpleTestCase

from config.urls import resolve_frontend_html


class ResolveFrontendHtmlTests(SimpleTestCase):
    FILES = [
        'index.html', 'login.html', 'bookings.html', 'search.html',
        'property/0.html', 'admin/properties/0.html', 'admin/properties.html',
        'owner/properties/manage.html',
    ]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        for name in self.FILES:
            path = os.path.join(self.root, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(name)
        # A file outside the static root that must never be served
        self.outside = os.path.join(os.path.dirname(self.root), 'secret.html')
        with open(self.outside, 'w', encoding='utf-8') as f:
            f.write('secret')

    def tearDown(self):
        self.tmp.cleanup()
        if os.path.exists(self.outside):
            os.remove(self.outside)

    def resolve(self, path):
        result = resolve_frontend_html(path, self.root)
        return result.replace(os.sep, '/') if result else result

    def test_root_and_static_pages(self):
        self.assertEqual(self.resolve(''), 'index.html')
        self.assertEqual(self.resolve('login'), 'login.html')
        self.assertEqual(self.resolve('bookings'), 'bookings.html')
        self.assertEqual(self.resolve('owner/properties/manage'), 'owner/properties/manage.html')

    def test_property_uuid_serves_property_shell_not_home(self):
        self.assertEqual(self.resolve('property/3f2c7a9e-1b2d-4c5e-8f90-123456789abc'), 'property/0.html')
        self.assertEqual(self.resolve('property/3f2c7a9e-1b2d-4c5e-8f90-123456789abc/'), 'property/0.html')

    def test_admin_property_uuid_serves_admin_detail_shell(self):
        self.assertEqual(self.resolve('admin/properties/3f2c7a9e-1b2d-4c5e-8f90-123456789abc'), 'admin/properties/0.html')

    def test_admin_property_list_is_not_treated_as_detail(self):
        self.assertEqual(self.resolve('admin/properties'), 'admin/properties.html')

    def test_deeper_or_unknown_paths_fall_back_to_app_shell(self):
        self.assertEqual(self.resolve('property/abc/extra'), 'index.html')
        self.assertEqual(self.resolve('no-such-page'), 'index.html')

    def test_path_traversal_is_never_served(self):
        self.assertEqual(self.resolve('../secret'), 'index.html')
        self.assertEqual(self.resolve('property/../../secret'), 'index.html')

    def test_unbuilt_frontend_returns_none(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertIsNone(resolve_frontend_html('property/abc', empty))
