/**
 * Google Analytics 4 (gtag.js) - privacy-safe event helpers.
 *
 * - Loads nothing and sends nothing unless NEXT_PUBLIC_GA_MEASUREMENT_ID is
 *   set to a valid GA4 id (G-XXXXXXXX) at build time.
 * - Every event goes through an allow-list: only the fields listed in
 *   EVENT_FIELDS below are sent, each type-checked and length-limited.
 *   Names, emails, phone/WhatsApp numbers, booking references, prices,
 *   payment data and tokens are never accepted.
 * - Page views send the pathname only (query strings are dropped - they can
 *   carry property ids for management pages and booking references).
 *
 * Kept free of path aliases and TS-only syntax so `node --test` can run the
 * unit tests directly (see analytics.test.mjs).
 */

export type AnalyticsEvent =
  | 'property_view'
  | 'property_search'
  | 'booking_start'
  | 'booking_created'
  | 'owner_property_submitted'

type FieldKind = 'id' | 'text' | 'count'

/** The ONLY parameters each event may carry. */
export const EVENT_FIELDS: Record<AnalyticsEvent, Record<string, FieldKind>> = {
  property_view: { property_id: 'id', property_type: 'text', city: 'text' },
  property_search: { destination: 'text', property_type: 'text', guest_count: 'count' },
  booking_start: { property_id: 'id', nights: 'count' },
  booking_created: { property_id: 'id', nights: 'count' },
  owner_property_submitted: { property_id: 'id' },
}

const MEASUREMENT_ID_PATTERN = /^G-[A-Z0-9]{4,20}$/
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const TEXT_MAX = 60
// Free text that looks like contact data is dropped rather than sent
const EMAIL_LIKE = /@/
const PHONE_LIKE = /\d[\d\s()+-]{6,}\d/

/** The configured GA4 measurement id, or null when analytics must stay off. */
export function getMeasurementId(): string | null {
  const id = (process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID || '').trim()
  return MEASUREMENT_ID_PATTERN.test(id) ? id : null
}

export function isAnalyticsEnabled(): boolean {
  return getMeasurementId() !== null
}

function cleanValue(kind: FieldKind, value: unknown): string | number | undefined {
  if (kind === 'id') {
    return typeof value === 'string' && UUID_PATTERN.test(value) ? value.toLowerCase() : undefined
  }
  if (kind === 'count') {
    const number = typeof value === 'string' ? Number(value) : value
    return typeof number === 'number' && Number.isInteger(number) && number >= 0 && number <= 365 ? number : undefined
  }
  if (typeof value !== 'string') return undefined
  const text = value.replace(/\s+/g, ' ').trim().slice(0, TEXT_MAX)
  if (!text || EMAIL_LIKE.test(text) || PHONE_LIKE.test(text)) return undefined
  return text
}

/** Keep only the allowed, valid fields of an event - everything else is discarded. */
export function sanitizeEventParams(event: AnalyticsEvent, params: Record<string, unknown> = {}): Record<string, string | number> {
  const allowed = EVENT_FIELDS[event]
  const clean: Record<string, string | number> = {}
  if (!allowed) return clean
  for (const [field, kind] of Object.entries(allowed)) {
    const value = cleanValue(kind, params[field])
    if (value !== undefined) clean[field] = value
  }
  return clean
}

/** Pathname only - drops query string and fragment. */
export function pagePath(pathOrUrl: string): string {
  const path = (pathOrUrl || '/').split(/[?#]/)[0]
  return path.startsWith('/') ? path : `/${path}`
}

type Gtag = (...args: unknown[]) => void

/**
 * Set up the standard gtag command queue (window.dataLayer + window.gtag)
 * and configure GA4 with automatic page views OFF. Safe to call repeatedly.
 * Commands queued before gtag.js finishes loading are processed in order.
 */
export function initAnalytics(): boolean {
  const id = getMeasurementId()
  if (!id || typeof window === 'undefined') return false
  const w = window as unknown as { dataLayer?: unknown[]; gtag?: Gtag; __slbGaConfigured?: string }
  if (w.__slbGaConfigured === id) return true
  w.dataLayer = w.dataLayer || []
  if (typeof w.gtag !== 'function') {
    // gtag.js reads the `arguments` object itself, not a copied array
    w.gtag = function gtag() {
      // eslint-disable-next-line prefer-rest-params
      w.dataLayer!.push(arguments)
    }
  }
  w.gtag('js', new Date())
  w.gtag('config', id, { send_page_view: false })
  w.__slbGaConfigured = id
  return true
}

function gtag(): Gtag | null {
  // Idempotent - also makes events fired before <GoogleAnalytics/> mounts safe
  if (!initAnalytics()) return null
  const fn = (window as unknown as { gtag?: Gtag }).gtag
  return typeof fn === 'function' ? fn : null
}

export function trackPageView(pathname: string): void {
  const send = gtag()
  if (!send) return
  const path = pagePath(pathname)
  send('event', 'page_view', { page_path: path, page_location: `${window.location.origin}${path}` })
}

export function trackEvent(event: AnalyticsEvent, params: Record<string, unknown> = {}): void {
  const send = gtag()
  if (!send) return
  send('event', event, sanitizeEventParams(event, params))
}

/** Whole nights between two ISO dates (YYYY-MM-DD), or undefined. */
export function nightsBetween(checkIn?: string, checkOut?: string): number | undefined {
  if (!checkIn || !checkOut) return undefined
  const nights = Math.round((Date.parse(checkOut) - Date.parse(checkIn)) / 86_400_000)
  return Number.isFinite(nights) && nights > 0 ? nights : undefined
}
