"""
Focused tests for CsrfExemptForJWTMiddleware proving:
- Bearer-authenticated requests bypass CSRF enforcement.
- Requests without a Bearer header remain subject to CSRF enforcement.
"""

from django.middleware.csrf import CsrfViewMiddleware
from django.test import RequestFactory, TestCase

from config.middleware import CsrfExemptForJWTMiddleware


def _dummy_view(request):
    return None


class CsrfExemptForJWTMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _run_through_middlewares(self, request):
        # Mirrors production MIDDLEWARE order: JWT middleware runs, then CsrfViewMiddleware.process_view.
        jwt_middleware = CsrfExemptForJWTMiddleware(lambda req: None)
        jwt_middleware(request)
        csrf_middleware = CsrfViewMiddleware(lambda req: None)
        return csrf_middleware.process_view(request, _dummy_view, (), {})

    def test_bearer_request_bypasses_csrf_enforcement(self):
        request = self.factory.post('/api/properties/', HTTP_AUTHORIZATION='Bearer faketoken123')
        result = self._run_through_middlewares(request)
        self.assertIsNone(result)
        self.assertTrue(getattr(request, '_dont_enforce_csrf_checks', False))

    def test_non_bearer_request_still_enforces_csrf(self):
        request = self.factory.post('/api/properties/')
        result = self._run_through_middlewares(request)
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 403)
        self.assertFalse(getattr(request, '_dont_enforce_csrf_checks', False))
