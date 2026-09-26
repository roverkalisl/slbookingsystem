"""
/ads.txt - production-equivalent tests.

Production routing: Cloudflare -> Render -> gunicorn -> Django. With
DEBUG=False (production, and always under the test runner) config/urls.py
registers the frontend catch-all, which answers unknown paths with the
Next.js 404 page. /ads.txt must be matched by its own route BEFORE that
catch-all and return the exact contents of frontend/public/ads.txt.

Run with: python manage.py test config.tests_adsense
"""

import os
import shutil
import tempfile

from django.conf import settings
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import resolve

from config import adsense
from config.urls import serve_frontend

EXPECTED = 'google.com, pub-7289676285085159, DIRECT, f08c47fec0942fa0\n'
REPO_ADS_TXT = os.path.normpath(os.path.join(settings.BASE_DIR, os.pardir, 'frontend', 'public', 'ads.txt'))
NEXT_404_PAGE = '<html><head><title>404: This page could not be found.</title></head><body>404</body></html>'


class AdsTxtSourceFileTestCase(SimpleTestCase):
    def test_frontend_public_ads_txt_has_the_exact_publisher_line(self):
        with open(REPO_ADS_TXT, 'rb') as f:
            raw = f.read()
        self.assertEqual(raw.decode('utf-8'), EXPECTED)
        self.assertFalse(raw.startswith(b'\xef\xbb\xbf'), 'no BOM')


class AdsTxtProductionRoutingTestCase(TestCase):  # requests run inside a DB transaction (ATOMIC_REQUESTS)
    """The deployed layout: STATIC_ROOT holds the exported frontend (incl. 404.html)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        with open(os.path.join(self.tmp.name, '404.html'), 'w', encoding='utf-8') as f:
            f.write(NEXT_404_PAGE)
        with open(os.path.join(self.tmp.name, 'index.html'), 'w', encoding='utf-8') as f:
            f.write('<html><head><title>home</title></head><body>home</body></html>')
        self.static = override_settings(STATIC_ROOT=self.tmp.name)
        self.static.enable()

    def tearDown(self):
        self.static.disable()
        self.tmp.cleanup()

    def test_production_catch_all_is_active_and_ads_txt_is_matched_before_it(self):
        self.assertFalse(settings.DEBUG)
        self.assertIs(resolve('/no-such-page').func, serve_frontend)  # production catch-all registered
        self.assertIs(resolve('/ads.txt').func, adsense.ads_txt)       # ...but /ads.txt has its own route

    def test_ads_txt_from_the_deployed_build(self):
        # build.sh copies frontend/out/* (which contains ads.txt) into STATIC_ROOT
        shutil.copyfile(REPO_ADS_TXT, os.path.join(self.tmp.name, 'ads.txt'))
        response = self.client.get('/ads.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=utf-8')
        self.assertEqual(response.content.decode('utf-8'), EXPECTED)
        self.assertNotIn(b'<html', response.content)

    def test_ads_txt_falls_back_to_frontend_public_when_the_build_has_no_copy(self):
        response = self.client.get('/ads.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), EXPECTED)

    def test_ads_txt_is_404_only_when_no_file_exists_anywhere(self):
        missing = os.path.join(self.tmp.name, 'nope', 'ads.txt')
        original = adsense.SOURCE_ADS_TXT
        adsense.SOURCE_ADS_TXT = missing
        try:
            response = self.client.get('/ads.txt')
        finally:
            adsense.SOURCE_ADS_TXT = original
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=utf-8')

    def test_unknown_paths_still_get_the_next_404_page(self):
        response = self.client.get('/no-such-page')
        self.assertEqual(response.status_code, 404)
        self.assertIn('could not be found', response.content.decode())

    def test_django_does_not_add_the_adsense_script_itself(self):
        # The Next.js frontend loads it (public pages only) - never twice
        html = serve_frontend(RequestFactory().get('/'), path='').content.decode()
        self.assertNotIn('googlesyndication', html)
