"""
Server-side property view counting (public property page only).

A view is counted at most once per property, per visitor, per day. The
visitor is identified by a one-way HMAC of IP address + browser identifier +
day, keyed with SECRET_KEY: no raw IP, user id, email or phone is stored,
and the hash changes every day so visitors cannot be followed across days.
"""

import hashlib
import hmac

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Property, PropertyView


def client_ip(request) -> str:
    """
    The visitor's IP address. Behind Render's proxy the real client address is
    the LAST entry of X-Forwarded-For (earlier entries can be set by the
    client); locally it is REMOTE_ADDR.
    """
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        last = forwarded.split(',')[-1].strip()
        if last:
            return last
    return request.META.get('REMOTE_ADDR', '') or ''


def visitor_fingerprint(request, day) -> str:
    """HMAC-SHA256(SECRET_KEY, ip | user agent | day) as 64 hex characters."""
    user_agent = (request.META.get('HTTP_USER_AGENT', '') or '')[:512]
    message = f'{client_ip(request)}|{user_agent}|{day.isoformat()}'.encode('utf-8')
    return hmac.new(settings.SECRET_KEY.encode('utf-8'), message, hashlib.sha256).hexdigest()


def is_excluded_viewer(user, property_obj: Property) -> bool:
    """The property's own owner and admins are never counted."""
    if not user or not user.is_authenticated:
        return False
    return bool(user.is_staff or user.is_superuser or property_obj.owner_id == user.id)


def record_property_view(property_obj: Property, request) -> bool:
    """
    Count one view of an APPROVED property. Returns True when a new daily
    view was stored, False when it was excluded or already counted today.
    """
    if property_obj.status != 'approved' or is_excluded_viewer(request.user, property_obj):
        return False
    today = timezone.localdate()
    visitor = visitor_fingerprint(request, today)
    try:
        # The unique constraint is the real guard: a concurrent duplicate
        # fails here instead of adding a second row.
        with transaction.atomic():
            PropertyView.objects.create(property=property_obj, viewed_on=today, visitor_hash=visitor)
        return True
    except IntegrityError:
        return False
