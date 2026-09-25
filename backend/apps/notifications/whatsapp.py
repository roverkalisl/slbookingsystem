"""
WhatsApp click-to-chat helpers (https://wa.me/<number>?text=<message>).

This is the single place that normalises phone numbers for WhatsApp and
builds wa.me links. It sends nothing itself - automated WhatsApp messages
are logged separately by WhatsAppNotification.

Where a booking's owner contact comes from (no number is copied onto the
booking; it is resolved live):
    Booking -> Property -> PropertyContact.whatsapp_number (the property's
    published WhatsApp contact) -> otherwise the property owner's User.phone.
"""

import re
from typing import Optional
from urllib.parse import quote

from django.core.exceptions import ObjectDoesNotExist

# Sri Lanka - numbers written in local form (0771234567 / 771234567) get this prefix.
DEFAULT_COUNTRY_CODE = '94'
# E.164: at most 15 digits including the country code.
MIN_DIGITS = 8
MAX_DIGITS = 15


def normalize_whatsapp_number(raw: Optional[str], default_country_code: str = DEFAULT_COUNTRY_CODE) -> Optional[str]:
    """
    Normalise a phone number to international digits-only form as used by
    wa.me (e.g. '+94 77 123 4567', '0771234567', '0094771234567' ->
    '94771234567'). Returns None when the value is empty or not a plausible
    international number.
    """
    if not raw:
        return None
    text = str(raw).strip()
    digits = re.sub(r'\D', '', text)
    if not digits:
        return None

    if text.startswith('+'):
        pass                                           # already international
    elif digits.startswith('00'):
        digits = digits[2:]                            # 00 international prefix
    elif digits.startswith('0'):
        digits = default_country_code + digits[1:]     # local trunk prefix 0
    elif default_country_code == '94' and len(digits) == 9:
        digits = default_country_code + digits         # Sri Lankan number without the 0

    if digits.startswith('0') or not (MIN_DIGITS <= len(digits) <= MAX_DIGITS):
        return None
    return digits


def whatsapp_url(number: Optional[str], message: str = '') -> Optional[str]:
    """wa.me link for an already-normalised number, with a URL-encoded prefilled message."""
    if not number:
        return None
    url = f'https://wa.me/{number}'
    if message:
        url += f'?text={quote(message, safe="")}'
    return url


def owner_whatsapp_number(property_obj) -> Optional[str]:
    """
    The WhatsApp number guests should use for this property: its published
    WhatsApp contact if valid, else the owner's own phone. None if neither
    is set or valid.
    """
    try:
        contact = property_obj.contact
    except ObjectDoesNotExist:  # no PropertyContact row for this property
        contact = None
    candidates = [contact.whatsapp_number if contact else None, property_obj.owner.phone]
    for candidate in candidates:
        number = normalize_whatsapp_number(candidate)
        if number:
            return number
    return None


def booking_inquiry_message(booking) -> str:
    """Prefilled guest -> owner message for a booking."""
    guests = booking.number_of_adults + booking.number_of_children
    return (
        'Hello, I have a booking inquiry.\n'
        '\n'
        f'Property: {booking.property.name}\n'
        f'Booking Reference: {booking.booking_reference}\n'
        f'Check-in: {booking.check_in_date:%Y-%m-%d}\n'
        f'Check-out: {booking.check_out_date:%Y-%m-%d}\n'
        f'Guests: {guests}\n'
        '\n'
        'I would like to discuss/confirm my booking.'
    )


def booking_owner_whatsapp(booking) -> dict:
    """
    Owner WhatsApp contact for a booking:
    {'owner_whatsapp_number': '94771234567' | None, 'owner_whatsapp_url': 'https://wa.me/...' | None}.
    Callers must check the requester is allowed to see it (the booking's guest or an admin).
    """
    number = owner_whatsapp_number(booking.property)
    return {
        'owner_whatsapp_number': number,
        'owner_whatsapp_url': whatsapp_url(number, booking_inquiry_message(booking)),
    }
