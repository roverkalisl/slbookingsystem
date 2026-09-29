/**
 * WhatsApp click-to-chat links (https://wa.me/<digits>?text=<message>).
 * Number normalisation mirrors apps/notifications/whatsapp.py on the backend.
 */

const DEFAULT_COUNTRY_CODE = '94' // Sri Lanka

/** '+94 77 123 4567' / '0771234567' / '0094771234567' -> '94771234567'; null if not a plausible number. */
export function normalizeWhatsAppNumber(raw: string | null | undefined): string | null {
  if (!raw) return null
  const text = raw.trim()
  let digits = text.replace(/\D/g, '')
  if (!digits) return null

  if (text.startsWith('+')) {
    // already international
  } else if (digits.startsWith('00')) {
    digits = digits.slice(2)
  } else if (digits.startsWith('0')) {
    digits = DEFAULT_COUNTRY_CODE + digits.slice(1)
  } else if (digits.length === 9) {
    digits = DEFAULT_COUNTRY_CODE + digits
  }

  if (digits.startsWith('0') || digits.length < 8 || digits.length > 15) return null
  return digits
}

/** wa.me link with a URL-encoded prefilled message, or null when the number is missing/invalid. */
export function whatsappLink(phone: string | null | undefined, message: string): string | null {
  const number = normalizeWhatsAppNumber(phone)
  return number ? `https://wa.me/${number}?text=${encodeURIComponent(message)}` : null
}

/** tel: link in international format ('077 960 6117' -> 'tel:+94779606117'), or null when the number is missing/invalid. */
export function callLink(phone: string | null | undefined): string | null {
  const number = normalizeWhatsAppNumber(phone)
  return number ? `tel:+${number}` : null
}

/** Only ever open links that really point at WhatsApp (e.g. a URL returned by the API). */
export function safeWhatsAppUrl(url: string | null | undefined): string | null {
  return url && url.startsWith('https://wa.me/') ? url : null
}

/** Owner -> guest prefilled message for a booking (no payment details). */
export function guestWhatsAppMessage(booking: {
  guest_name?: string | null
  property_name?: string | null
  booking_reference: string
}): string {
  const name = (booking.guest_name || '').trim() || 'there'
  const property = (booking.property_name || '').trim() || 'your host'
  return `Hello ${name}, this is ${property} regarding your SL Booking reservation ${booking.booking_reference}.`
}

/** Owner -> guest WhatsApp link for a booking, or null when the guest has no valid number. */
export function guestWhatsAppLink(booking: {
  guest_phone?: string | null
  guest_name?: string | null
  property_name?: string | null
  booking_reference: string
}): string | null {
  return whatsappLink(booking.guest_phone, guestWhatsAppMessage(booking))
}
