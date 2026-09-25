/**
 * GA4 helper tests (src/lib/analytics.ts), run with Node's built-in test
 * runner - Node >= 22.18 / 23.6 strips the TypeScript types itself:
 *
 *   npm run test:analytics
 */
import { test, beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import {
  EVENT_FIELDS,
  getMeasurementId,
  initAnalytics,
  isAnalyticsEnabled,
  nightsBetween,
  pagePath,
  sanitizeEventParams,
  trackEvent,
  trackPageView,
} from '../src/lib/analytics.ts'

const PROPERTY_ID = '3f2c7a9e-1b2d-4c5e-8f90-123456789abc'

/** A fake browser window whose gtag records every call. */
function fakeWindow() {
  const calls = []
  globalThis.window = {
    location: { origin: 'https://slbooking.hotel.lk', pathname: '/search' },
    dataLayer: [],
    gtag: (...args) => calls.push(args),
  }
  return calls
}

beforeEach(() => {
  delete process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID
  delete globalThis.window
})

test('GA is disabled when the measurement id is absent or invalid', () => {
  assert.equal(getMeasurementId(), null)
  assert.equal(isAnalyticsEnabled(), false)
  for (const bad of ['', '   ', 'UA-12345-1', "G-ABC'); alert(1); ('", 'g-lowercase1']) {
    process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID = bad
    assert.equal(getMeasurementId(), null, bad)
  }
})

test('nothing is sent or initialised without a measurement id', () => {
  const calls = fakeWindow()
  trackPageView('/property/abc?x=1')
  trackEvent('property_view', { property_id: PROPERTY_ID })
  assert.equal(initAnalytics(), false)
  assert.deepEqual(calls, [])
  assert.deepEqual(globalThis.window.dataLayer, [])
})

test('a valid id enables GA and config disables automatic page views', () => {
  process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID = 'G-TEST12345'
  const calls = fakeWindow()
  assert.equal(isAnalyticsEnabled(), true)
  assert.equal(initAnalytics(), true)
  const config = calls.find((c) => c[0] === 'config')
  assert.deepEqual(config, ['config', 'G-TEST12345', { send_page_view: false }])
  initAnalytics() // idempotent
  assert.equal(calls.filter((c) => c[0] === 'config').length, 1)
})

test('page views send the pathname only - no query string or fragment', () => {
  process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID = 'G-TEST12345'
  const calls = fakeWindow()
  trackPageView('/bookings?booking_created=SLB-2026-0001#top')
  const pageView = calls.find((c) => c[1] === 'page_view')
  assert.deepEqual(pageView, ['event', 'page_view', {
    page_path: '/bookings',
    page_location: 'https://slbooking.hotel.lk/bookings',
  }])
  assert.equal(pagePath('owner/properties/manage?propertyId=1'), '/owner/properties/manage')
})

test('events carry only the approved fields', () => {
  process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID = 'G-TEST12345'
  const calls = fakeWindow()
  trackEvent('booking_created', {
    property_id: PROPERTY_ID,
    nights: 3,
    booking_reference: 'SLB-2026-0001',
    total_price: 45000,
    guest_email: 'guest@example.com',
    guest_name: 'Jane Doe',
    access_token: 'eyJhbGciOi...',
    card_number: '4242424242424242',
  })
  const event = calls.find((c) => c[1] === 'booking_created')
  assert.deepEqual(event, ['event', 'booking_created', { property_id: PROPERTY_ID, nights: 3 }])
})

test('every event allow-list contains only non-sensitive fields', () => {
  const allowed = new Set(['property_id', 'property_type', 'city', 'destination', 'guest_count', 'nights'])
  for (const [event, fields] of Object.entries(EVENT_FIELDS)) {
    for (const field of Object.keys(fields)) assert.ok(allowed.has(field), `${event}.${field}`)
  }
  assert.deepEqual(Object.keys(EVENT_FIELDS.owner_property_submitted), ['property_id'])
})

test('values are validated: ids, counts and free text', () => {
  assert.deepEqual(sanitizeEventParams('property_view', {
    property_id: 'not-a-uuid', property_type: 'Hotel', city: 'Kandy',
  }), { property_type: 'Hotel', city: 'Kandy' })
  assert.deepEqual(sanitizeEventParams('property_search', {
    destination: 'guest@example.com', property_type: 'Villa', guest_count: 4,
  }), { property_type: 'Villa', guest_count: 4 })
  // Phone / WhatsApp-like text is dropped
  assert.deepEqual(sanitizeEventParams('property_search', { destination: '+94 77 123 4567' }), {})
  assert.deepEqual(sanitizeEventParams('booking_start', { property_id: PROPERTY_ID, nights: -2 }), { property_id: PROPERTY_ID })
  assert.deepEqual(sanitizeEventParams('booking_start', { property_id: PROPERTY_ID, nights: 2.5 }), { property_id: PROPERTY_ID })
  assert.equal(sanitizeEventParams('property_view', { city: 'x'.repeat(200) }).city.length, 60)
  assert.deepEqual(sanitizeEventParams('unknown_event', { property_id: PROPERTY_ID }), {})
})

test('nightsBetween', () => {
  assert.equal(nightsBetween('2026-10-01', '2026-10-04'), 3)
  assert.equal(nightsBetween('2026-10-04', '2026-10-01'), undefined)
  assert.equal(nightsBetween('', '2026-10-01'), undefined)
})
