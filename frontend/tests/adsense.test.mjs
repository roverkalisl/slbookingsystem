/**
 * AdSense helpers (src/lib/adsense.ts) and the ads.txt file.
 *
 *   npm run test:unit
 */
import { test, beforeEach } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  getAdSenseClient, getAdSenseScriptSrc, isNoIndexPage, isPrivatePath, needsAdFreeReload, PRIVATE_PATH_PREFIXES,
} from '../src/lib/adsense.ts'

const docWith = (hasScript) => ({ querySelector: (selector) => (hasScript && selector.includes('pagead2.googlesyndication.com') ? {} : null) })

beforeEach(() => { delete process.env.NEXT_PUBLIC_ADSENSE_PUBLISHER_ID })

test('publisher id comes only from NEXT_PUBLIC_ADSENSE_PUBLISHER_ID', () => {
  assert.equal(getAdSenseClient(), null)
  assert.equal(getAdSenseScriptSrc(), null)
  process.env.NEXT_PUBLIC_ADSENSE_PUBLISHER_ID = 'pub-7289676285085159'
  assert.equal(getAdSenseClient(), 'ca-pub-7289676285085159')
  assert.equal(getAdSenseScriptSrc(),
    'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7289676285085159')
})

test('malformed publisher ids disable AdSense', () => {
  for (const bad of ['pub-123', 'ca-pub-7289676285085159', 'pub-7289676285085159"><script>', ' ', 'PUB-7289676285085159']) {
    process.env.NEXT_PUBLIC_ADSENSE_PUBLISHER_ID = bad
    assert.equal(getAdSenseClient(), null, bad)
  }
})

test('private pages never load ads', () => {
  for (const path of ['/admin/dashboard', '/admin', '/owner/properties/manage', '/owner', '/login', '/register',
    '/bookings', '/bookings?payment=success', '/booking/abc', 'owner/calendar']) {
    assert.equal(isPrivatePath(path), true, path)
  }
  assert.deepEqual(PRIVATE_PATH_PREFIXES, ['admin', 'owner', 'login', 'register', 'bookings', 'booking'])
})

test('public pages are eligible', () => {
  for (const path of ['/', '', null, '/search', '/search?destination=Kandy', '/property/abc', '/about', '/administrator-guide']) {
    assert.equal(isPrivatePath(path), false, String(path))
  }
})

test('reload only when a private page still has the ads script (no reload loop)', () => {
  assert.equal(needsAdFreeReload('/owner/dashboard', docWith(true)), true)
  assert.equal(needsAdFreeReload('/owner/dashboard', docWith(false)), false)
  assert.equal(needsAdFreeReload('/search', docWith(true)), false)
  assert.equal(needsAdFreeReload('/login', undefined), false)
})

test('noindex pages (e.g. the 404 page) are not eligible', () => {
  const noindex = { querySelector: (s) => (s.includes('robots') ? {} : null) }
  const normal = { querySelector: () => null }
  assert.equal(isNoIndexPage(noindex), true)
  assert.equal(isNoIndexPage(normal), false)
  assert.equal(isNoIndexPage(undefined), false)
})

test('public/ads.txt contains exactly the AdSense line', () => {
  const raw = readFileSync(new URL('../public/ads.txt', import.meta.url), 'utf8')
  assert.equal(raw, 'google.com, pub-7289676285085159, DIRECT, f08c47fec0942fa0\n')
})
