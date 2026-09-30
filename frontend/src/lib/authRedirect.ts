/**
 * Return-to-booking after login.
 *
 * A guest who clicks Book Now while signed out is sent to
 * /login?next=/property/<id>?room=..&check_in=..&check_out=..&guests=.. and,
 * after signing in, back to that exact property with the booking form refilled.
 * `next` is only ever honoured as a same-site path (never an external URL).
 */

type RoleUser = { roles?: string[]; is_staff?: boolean; is_superuser?: boolean } | null | undefined

export interface BookingDraft {
  roomTypeId?: string
  checkIn?: string
  checkOut?: string
  guests?: number
}

const INTERNAL_ORIGIN = 'https://slbooking.internal'
// Returning to these after login would loop or make no sense.
const NON_RETURN_PATHS = ['/login', '/register']
const MAX_RETURN_LENGTH = 2048
const ROOM_ID = /^[A-Za-z0-9-]{1,64}$/
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/
const MAX_GUESTS = 50

/** Landing page for a role - unchanged from the original login page. */
export function getRoleHome(user: RoleUser): string {
  if (user?.is_staff || user?.is_superuser || user?.roles?.includes('super_admin')) {
    return '/admin/dashboard'
  }
  if (user?.roles?.includes('property_owner')) return '/owner/dashboard'
  return '/search'
}

/**
 * The internal path to return to, or null. Rejects absolute/protocol-relative
 * URLs ('https://x', '//x', '/\x'), backslashes, whitespace/control characters
 * and the login/register pages themselves.
 */
export function safeReturnPath(raw: unknown): string | null {
  if (typeof raw !== 'string' || !raw || raw.length > MAX_RETURN_LENGTH) return null
  if (!raw.startsWith('/') || raw.startsWith('//') || /[\\\s\u0000-\u001f\u007f]/.test(raw)) return null

  let url: URL
  try {
    url = new URL(raw, INTERNAL_ORIGIN)
  } catch {
    return null
  }
  if (url.origin !== INTERNAL_ORIGIN) return null
  // Encoded control characters or slashes/backslashes have no place in an app path.
  if (/%(?:[01][0-9a-f]|7f|2f|5c)/i.test(url.pathname)) return null

  const path = url.pathname.replace(/\/+$/, '') || '/'
  if (NON_RETURN_PATHS.includes(path.toLowerCase())) return null
  return `${url.pathname}${url.search}${url.hash}`
}

/** The safe `next` path from a login page query string ('?next=...'), or null. */
export function returnPathFromSearch(search: string | null | undefined): string | null {
  return safeReturnPath(new URLSearchParams(search || '').get('next'))
}

/** '/login?next=<encoded path>' for a safe internal path, plain '/login' otherwise. */
export function loginUrl(returnTo?: string | null): string {
  const path = safeReturnPath(returnTo)
  return path ? `/login?next=${encodeURIComponent(path)}` : '/login'
}

/**
 * Where to go after signing in. Admins and owners keep their dashboards;
 * guests return to the page they came from (e.g. the property they were
 * booking), or /search when there is none.
 */
export function postLoginDestination(user: RoleUser, returnPath?: string | null): string {
  const home = getRoleHome(user)
  if (home !== '/search') return home
  return safeReturnPath(returnPath) ?? home
}

/** '/register?next=<encoded path>' for a safe internal path, plain '/register' otherwise. */
export function registerUrl(returnTo?: string | null): string {
  const path = safeReturnPath(returnTo)
  return path ? `/register?next=${encodeURIComponent(path)}` : '/register'
}

/**
 * Where to go after registering. Owners (and any non-guest) keep the existing
 * /bookings landing; guests return to the page they came from (e.g. the
 * property they were booking), or /search when there is none.
 */
export function postRegisterDestination(user: RoleUser, returnPath?: string | null): string {
  if (getRoleHome(user) !== '/search') return '/bookings'
  return safeReturnPath(returnPath) ?? '/search'
}

/**
 * Navigate after login/registration. Returning to the saved page is a full
 * page load: dynamic pages (/property/<id>) read their real id and the saved
 * booking form from the URL on mount. Role landing pages use the router.
 */
export function goAfterAuth(
  destination: string,
  returnPath: string | null,
  push: (href: string) => void,
  assign: (href: string) => void = (href) => window.location.assign(href),
): void {
  if (returnPath && destination === returnPath) assign(destination)
  else push(destination)
}

/** Property URL carrying the booking form state (never the guest's phone number). */
export function bookingReturnPath(propertyPath: string, draft: BookingDraft): string {
  const params = new URLSearchParams()
  if (draft.roomTypeId && ROOM_ID.test(draft.roomTypeId)) params.set('room', draft.roomTypeId)
  if (isIsoDate(draft.checkIn)) params.set('check_in', draft.checkIn)
  if (isIsoDate(draft.checkOut)) params.set('check_out', draft.checkOut)
  if (isGuestCount(draft.guests)) params.set('guests', String(draft.guests))
  const query = params.toString()
  return query ? `${propertyPath}?${query}` : propertyPath
}

/** Booking form state from a property page query string; invalid values are dropped. */
export function parseBookingDraft(search: string | null | undefined): BookingDraft {
  const params = new URLSearchParams(search || '')
  const draft: BookingDraft = {}
  const room = params.get('room')
  const checkIn = params.get('check_in')
  const checkOut = params.get('check_out')
  const guests = Number(params.get('guests'))
  if (room && ROOM_ID.test(room)) draft.roomTypeId = room
  if (isIsoDate(checkIn)) draft.checkIn = checkIn
  if (isIsoDate(checkOut) && (!draft.checkIn || checkOut > draft.checkIn)) draft.checkOut = checkOut
  if (params.has('guests') && isGuestCount(guests)) draft.guests = guests
  return draft
}

/**
 * Book Now: the login URL (returning to this booking) for a signed-out guest,
 * or null when the guest is signed in and the booking should go ahead.
 */
export function bookingLoginRedirect(isAuthenticated: boolean, returnPath: string): string | null {
  return isAuthenticated ? null : loginUrl(returnPath)
}

function isIsoDate(value: string | null | undefined): value is string {
  if (!value || !ISO_DATE.test(value)) return false
  const date = new Date(`${value}T00:00:00Z`)
  return !Number.isNaN(date.getTime()) && date.toISOString().startsWith(value)
}

function isGuestCount(value: number | undefined): value is number {
  return Number.isInteger(value) && (value as number) >= 1 && (value as number) <= MAX_GUESTS
}
