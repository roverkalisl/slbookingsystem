"""
Custom middleware for CSRF exemption for JWT-authenticated requests.

Rationale:
- Django CSRF protection is designed for session/cookie-based authentication
- JWT authentication is inherently safe from CSRF attacks (token in header, not cookie)
- DRF API endpoints using only JWTAuthentication don't require CSRF protection
- This middleware exempts requests with valid JWT from CSRF checks while keeping
  CSRF protection for form endpoints and session-based endpoints
"""

import logging

logger = logging.getLogger(__name__)


class CsrfExemptForJWTMiddleware:
    """
    Exempts JWT-authenticated requests from CSRF validation.

    If the request has an Authorization header with Bearer token (JWT),
    mark it as CSRF-exempt since JWT provides its own security.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if request has JWT token in Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if auth_header.startswith('Bearer '):
            # This is the attribute CsrfViewMiddleware actually checks to skip enforcement
            request._dont_enforce_csrf_checks = True
            logger.debug(f"JWT token detected, exempting {request.method} {request.path} from CSRF")

        response = self.get_response(request)
        return response
