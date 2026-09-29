/**
 * WhatsApp helper tests (src/lib/whatsapp.ts), run with Node's built-in test
 * runner - Node >= 22.18 / 23.6 strips the TypeScript types itself:
 *
 *   npm run test:unit
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  guestWhatsAppLink,
  guestWhatsAppMessage,
  normalizeWhatsAppNumber,
} from '../src/lib/whatsapp.ts'

const booking = {
  guest_name: 'Nimal Perera',
  property_name: 'Sea Villa',
  booking_reference: 'BK2026ABC',
  guest_phone: '+94771234567',
}

test('valid Sri Lankan and international numbers normalise to wa.me digits', () => {
  for (const raw of ['0771234567', '771234567', '+94771234567', '+94 77 123 4567', '0094771234567', '077-123-4567']) {
    assert.equal(normalizeWhatsAppNumber(raw), '94771234567', raw)
  }
  assert.equal(normalizeWhatsAppNumber('+44 7911 123456'), '447911123456')
})

test('invalid numbers are rejected', () => {
  for (const raw of [null, undefined, '', 'abc', '123', '+0771234567', '+1234567890123456']) {
    assert.equal(normalizeWhatsAppNumber(raw), null, String(raw))
  }
})

test('owner -> guest message uses the agreed wording and no payment details', () => {
  const message = guestWhatsAppMessage(booking)
  assert.equal(message, 'Hello Nimal Perera, this is Sea Villa regarding your SL Booking reservation BK2026ABC.')
  assert.doesNotMatch(message, /LKR|price|total|pay/i)
})

test('owner -> guest link is a wa.me link with the encoded message', () => {
  const url = guestWhatsAppLink(booking)
  assert.equal(url, `https://wa.me/94771234567?text=${encodeURIComponent(guestWhatsAppMessage(booking))}`)
})

test('no WhatsApp link when the guest has no valid number (older bookings)', () => {
  for (const guest_phone of [undefined, null, '', 'n/a', '123']) {
    assert.equal(guestWhatsAppLink({ ...booking, guest_phone }), null, String(guest_phone))
  }
})
