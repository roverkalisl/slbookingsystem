/**
 * Google AdSense Auto Ads - configuration and page eligibility for
 * <AdSense/> (components/AdSense.tsx).
 *
 * The publisher id comes ONLY from NEXT_PUBLIC_ADSENSE_PUBLISHER_ID
 * (pub-XXXXXXXXXXXXXXXX), read when the frontend is built. When it is unset
 * or malformed, no AdSense script is loaded anywhere.
 *
 * Kept free of path aliases / TS-only syntax so `node --test` can run it.
 */

export const ADSENSE_SCRIPT_URL = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js'
export const ADSENSE_SCRIPT_HOST = 'pagead2.googlesyndication.com'

const PUBLISHER_ID_PATTERN = /^pub-\d{16}$/

/** Management, account and checkout pages - never eligible for ads. */
export const PRIVATE_PATH_PREFIXES = ['admin', 'owner', 'login', 'register', 'bookings', 'booking']

/** 'ca-pub-XXXXXXXXXXXXXXXX' for the configured publisher, or null when AdSense is off. */
export function getAdSenseClient(): string | null {
  const id = (process.env.NEXT_PUBLIC_ADSENSE_PUBLISHER_ID || '').trim()
  return PUBLISHER_ID_PATTERN.test(id) ? `ca-${id}` : null
}

/** The official Auto Ads script URL for the configured publisher, or null. */
export function getAdSenseScriptSrc(): string | null {
  const client = getAdSenseClient()
  return client ? `${ADSENSE_SCRIPT_URL}?client=${client}` : null
}

/** Admin, owner, login/register and the guest's bookings/payment pages never show ads. */
export function isPrivatePath(pathname: string | null | undefined): boolean {
  const first = (pathname || '/').split(/[?#]/)[0].replace(/^\/+/, '').split('/')[0].toLowerCase()
  return PRIVATE_PATH_PREFIXES.includes(first)
}

/** Pages marked <meta name="robots" content="noindex"> (e.g. the 404 page) carry no publisher content - no ads. */
export function isNoIndexPage(doc: { querySelector: (selector: string) => unknown } | undefined): boolean {
  return !!doc?.querySelector('meta[name="robots"][content*="noindex"]')
}

/** True when the AdSense script is already on the current page. */
export function adSenseScriptLoaded(doc: { querySelector: (selector: string) => unknown } | undefined): boolean {
  return !!doc?.querySelector(`script[src*="${ADSENSE_SCRIPT_HOST}"]`)
}

/**
 * After a client-side navigation into a private page, the script loaded by
 * the public page it came from would stay active - so that private page is
 * reloaded once (the fresh load renders no AdSense script there).
 */
export function needsAdFreeReload(pathname: string | null | undefined, doc: { querySelector: (selector: string) => unknown } | undefined): boolean {
  return isPrivatePath(pathname) && adSenseScriptLoaded(doc)
}
