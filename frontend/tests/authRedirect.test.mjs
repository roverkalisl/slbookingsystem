/**
 * Return-to-booking after login (src/lib/authRedirect.ts), used by the
 * property page's Book Now and the login page.
 *
 *   npm run test:unit
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  bookingLoginRedirect, bookingReturnPath, getRoleHome, goAfterAuth, loginUrl, parseBookingDraft,
  postLoginDestination, postRegisterDestination, registerUrl, returnPathFromSearch, safeReturnPath,
} from '../src/lib/authRedirect.ts'

const VILLA = '3f2c7a9e-1b2d-4c5e-8f90-123456789abc' // e.g. Thuru Sevena Villa
const ROOM = 'a1b2c3d4-0000-4000-8000-000000000001'
const DRAFT = { roomTypeId: ROOM, checkIn: '2026-12-20', checkOut: '2026-12-23', guests: 3 }
const BOOKING_PATH = `/property/${VILLA}?room=${ROOM}&check_in=2026-12-20&check_out=2026-12-23&guests=3`

const GUEST = { roles: ['guest'] }
const OWNER = { roles: ['property_owner'] }
const ADMIN = { roles: ['super_admin'] }

/** What the login page does: read ?next= from its own URL and pick the destination. */
const afterLogin = (user, loginHref) => postLoginDestination(user, returnPathFromSearch(new URL(loginHref, 'https://slbooking.hotel.lk').search))

test('unauthenticated guest starting a booking is sent to login with the booking as ?next=', () => {
  const returnPath = bookingReturnPath(`/property/${VILLA}`, DRAFT)
  assert.equal(returnPath, BOOKING_PATH)
  const redirect = bookingLoginRedirect(false, returnPath)
  assert.equal(redirect, `/login?next=${encodeURIComponent(BOOKING_PATH)}`)
})

test('after a successful guest login they return to the exact property and booking form', () => {
  const loginHref = bookingLoginRedirect(false, bookingReturnPath(`/property/${VILLA}`, DRAFT))
  const destination = afterLogin(GUEST, loginHref)
  assert.equal(destination, BOOKING_PATH)
  for (const wrong of ['/search', '/bookings', '/owner/dashboard', '/admin/dashboard']) assert.notEqual(destination, wrong)
  // The property page restores the form from that URL.
  assert.deepEqual(parseBookingDraft(new URL(destination, 'https://x').search), DRAFT)
})

test('an Entry Villa / partly filled form still returns to the property', () => {
  const path = bookingReturnPath(`/property/${VILLA}`, { roomTypeId: '', checkIn: '', checkOut: '', guests: 2 })
  assert.equal(path, `/property/${VILLA}?guests=2`)
  assert.equal(afterLogin(GUEST, loginUrl(path)), path)
  assert.equal(bookingReturnPath(`/property/${VILLA}`, {}), `/property/${VILLA}`)
})

test('an authenticated guest goes straight to the booking (no login redirect)', () => {
  assert.equal(bookingLoginRedirect(true, BOOKING_PATH), null)
})

test('guest login from the normal login page (no pending booking) goes to /search', () => {
  assert.equal(afterLogin(GUEST, '/login'), '/search')
  assert.equal(afterLogin({}, '/login'), '/search')
  assert.equal(afterLogin(null, '/login?next='), '/search')
})

test('owner login goes to /owner/dashboard, even with a pending booking', () => {
  assert.equal(afterLogin(OWNER, '/login'), '/owner/dashboard')
  assert.equal(afterLogin(OWNER, loginUrl(BOOKING_PATH)), '/owner/dashboard')
})

test('admin / superuser / staff login goes to /admin/dashboard, even with a pending booking', () => {
  for (const user of [ADMIN, { is_superuser: true }, { is_staff: true }, { roles: ['property_owner', 'super_admin'] }]) {
    assert.equal(afterLogin(user, '/login'), '/admin/dashboard', JSON.stringify(user))
    assert.equal(afterLogin(user, loginUrl(BOOKING_PATH)), '/admin/dashboard', JSON.stringify(user))
  }
  assert.equal(getRoleHome(GUEST), '/search')
})

test('malicious external return URLs are rejected and the guest lands on /search', () => {
  const attacks = [
    'https://evil.example/phish', 'http://evil.example', '//evil.example/x', '/\\evil.example', '\\\\evil.example',
    '/%0a//evil.example', '/%2F%2Fevil.example', '/%5cevil.example', '/\n//evil.example', '/\t/evil.example', ' //evil.example', 'javascript:alert(1)', 'data:text/html,x',
    'evil.example', 'HTTPS://evil.example', '/login', '/login?next=/search', '/register', `/${'a'.repeat(3000)}`,
  ]
  for (const next of attacks) {
    assert.equal(safeReturnPath(next), null, next)
    assert.equal(afterLogin(GUEST, `/login?next=${encodeURIComponent(next)}`), '/search', next)
    assert.equal(loginUrl(next), '/login', next)
  }
  for (const bad of [undefined, null, 42, {}, ['/search']]) assert.equal(safeReturnPath(bad), null)
})

test('safe internal paths are kept exactly, including query and hash', () => {
  for (const path of [BOOKING_PATH, '/search?destination=Galle', '/bookings', '/property/abc#reviews', '/']) {
    assert.equal(safeReturnPath(path), path)
  }
})

test('tampered booking form values are dropped, not used', () => {
  assert.deepEqual(parseBookingDraft('?room=<script>&check_in=2026-02-30&check_out=tomorrow&guests=-1'), {})
  assert.deepEqual(parseBookingDraft('?guests=1000&room=' + 'a'.repeat(65)), {})
  assert.deepEqual(parseBookingDraft('?check_in=2026-12-23&check_out=2026-12-20'), { checkIn: '2026-12-23' })
  assert.deepEqual(parseBookingDraft(''), {})
  assert.doesNotMatch(bookingReturnPath('/property/x', { ...DRAFT, guests: 0, checkIn: 'x' }), /guests|check_in=x/)
})

test('the property page and login page use these helpers (no hard-coded /login or role-only redirect)', () => {
  const property = readFileSync(new URL('../src/app/property/[id]/property-ui.tsx', import.meta.url), 'utf8')
  assert.match(property, /bookingLoginRedirect\(isAuthenticated, returnPath/)
  assert.match(property, /parseBookingDraft\(window\.location\.search\)/)
  assert.doesNotMatch(property, /href\s*=\s*['"]\/login['"]/)
  const returnArgs = property.match(/bookingReturnPath\([^{]*\{([^}]*)\}/)
  assert.ok(returnArgs, 'bookingReturnPath call found')
  assert.doesNotMatch(returnArgs[1], /phone/i, 'phone is never put in the URL')

  const login = readFileSync(new URL('../src/app/login/page.tsx', import.meta.url), 'utf8')
  assert.match(login, /postLoginDestination\(user, returnPath\)/)
  assert.match(login, /returnPathFromSearch\(window\.location\.search\)/)
  assert.doesNotMatch(login, /function getRoleHome/)
})

// ---- Sign-up path: Property -> Book Now -> Login -> Sign up -> Register ----

const searchOf = (href) => new URL(href, 'https://slbooking.hotel.lk').search
/** Login page "Sign up" link, built from the login page's own ?next=. */
const signUpLinkFrom = (loginHref) => registerUrl(returnPathFromSearch(searchOf(loginHref)))
/** What the register page does after a successful registration. */
const afterRegister = (user, registerHref) => postRegisterDestination(user, returnPathFromSearch(searchOf(registerHref)))

function signUpJourney(draft) {
  const loginHref = bookingLoginRedirect(false, bookingReturnPath(`/property/${VILLA}`, draft))
  const registerHref = signUpLinkFrom(loginHref)
  return { loginHref, registerHref, destination: afterRegister(GUEST, registerHref) }
}

test('property booking -> login -> sign up -> the original property', () => {
  const { loginHref, registerHref, destination } = signUpJourney(DRAFT)
  assert.equal(registerHref, `/register?next=${encodeURIComponent(BOOKING_PATH)}`)
  assert.equal(destination, BOOKING_PATH)
  assert.ok(destination.startsWith(`/property/${VILLA}?`))
  for (const wrong of ['/search', '/bookings', '/owner/dashboard', '/admin/dashboard']) assert.notEqual(destination, wrong)
  // "Sign in" on the register page leads back to the same login URL (no loss either way).
  assert.equal(loginUrl(returnPathFromSearch(searchOf(registerHref))), loginHref)
})

test('sign up preserves the room selection, dates and guest count', () => {
  const { destination } = signUpJourney(DRAFT)
  const restored = parseBookingDraft(searchOf(destination))
  assert.equal(restored.roomTypeId, ROOM)
  assert.equal(restored.checkIn, '2026-12-20')
  assert.equal(restored.checkOut, '2026-12-23')
  assert.equal(restored.guests, 3)
})

test('sign up with a malicious next is rejected: guest lands on /search, links stay plain', () => {
  for (const next of ['https://evil.example/phish', '//evil.example', '/\\evil.example', 'javascript:alert(1)', '/%2F%2Fevil.example', '/register']) {
    const registerHref = `/register?next=${encodeURIComponent(next)}`
    assert.equal(afterRegister(GUEST, registerHref), '/search', next)
    assert.equal(registerUrl(next), '/register', next)
    assert.equal(signUpLinkFrom(`/login?next=${encodeURIComponent(next)}`), '/register', next)
  }
})

test('the guest phone number never appears in any URL of the journey', () => {
  const phones = ['0771234567', '+94771234567', '94771234567']
  const withPhone = { ...DRAFT, guestPhone: '0771234567', guest_phone: '+94771234567', phone: '0771234567' }
  const urls = Object.values(signUpJourney(withPhone))
  for (const url of urls) {
    const decoded = decodeURIComponent(decodeURIComponent(url))
    assert.doesNotMatch(decoded, /phone/i, url)
    for (const phone of phones) assert.ok(!decoded.includes(phone), `${phone} in ${url}`)
  }
})

test('normal registration without next: guest -> /search, owner keeps /bookings', () => {
  for (const href of ['/register', '/register?next=', '/register?other=1']) {
    assert.equal(afterRegister(GUEST, href), '/search', href)
    assert.equal(afterRegister({ roles: [] }, href), '/search', href)
    assert.equal(afterRegister(OWNER, href), '/bookings', href)
  }
  assert.equal(registerUrl(null), '/register')
})

test('owner registration is unchanged even with a pending booking', () => {
  assert.equal(afterRegister(OWNER, registerUrl(BOOKING_PATH)), '/bookings')
})

test('goAfterAuth: full page load back to the saved page, router for role landing pages', () => {
  const calls = []
  const push = (href) => calls.push(['push', href])
  const assign = (href) => calls.push(['assign', href])
  goAfterAuth(BOOKING_PATH, BOOKING_PATH, push, assign)
  goAfterAuth('/search', null, push, assign)
  goAfterAuth('/bookings', BOOKING_PATH, push, assign)
  assert.deepEqual(calls, [['assign', BOOKING_PATH], ['push', '/search'], ['push', '/bookings']])
})

test('login "Sign up" and register page use the helpers (no hard-coded /bookings or /register redirect)', () => {
  const login = readFileSync(new URL('../src/app/login/page.tsx', import.meta.url), 'utf8')
  assert.match(login, /href=\{registerUrl\(returnPath\)\}/)
  assert.doesNotMatch(login, /href="\/register"/)

  const register = readFileSync(new URL('../src/app/register/page.tsx', import.meta.url), 'utf8')
  assert.match(register, /postRegisterDestination\(user, returnPath\)/)
  assert.match(register, /returnPathFromSearch\(window\.location\.search\)/)
  assert.match(register, /href=\{loginUrl\(returnPath\)\}/)
  assert.doesNotMatch(register, /router\.push\('\/bookings'\)/)
})
