/**
 * SL Booking Partner Network (src/lib/partnerNetwork.ts and
 * src/components/PartnerNetwork.tsx) on the Owner Dashboard.
 *
 *   npm run test:unit
 */
import { test, before } from 'node:test'
import assert from 'node:assert/strict'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import ts from 'typescript'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { PARTNERS, PARTNER_WHATSAPP_MESSAGE, partnerFacebookLink } from '../src/lib/partnerNetwork.ts'
import { callLink } from '../src/lib/whatsapp.ts'

const src = (path) => new URL(`../src/${path}`, import.meta.url)
const ENCODED_MESSAGE = encodeURIComponent(PARTNER_WHATSAPP_MESSAGE)

const EXPECTED = [
  { name: 'Pristine Moment Photography', phone: '077 960 6117', wa: '94779606117', tel: 'tel:+94779606117' },
  { name: 'Southern Garden Design & Maintain', phone: '+94 77 085 0820', wa: '94770850820', tel: 'tel:+94770850820' },
  { name: 'Virtue Hub Sri Lanka', phone: '074 094 8966', wa: '94740948966', tel: 'tel:+94740948966' },
]

/** Transpile the real TSX component (no extra test libraries) and load it with the @/lib imports resolved. */
async function loadComponent() {
  const { outputText } = ts.transpileModule(readFileSync(src('components/PartnerNetwork.tsx'), 'utf8'), {
    compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
  })
  const code = outputText.replace(/(['"])@\/lib\/([\w-]+)\1/g, (_, q, name) => `${q}${src(`lib/${name}.ts`).href}${q}`)
  // Inside node_modules so react / lucide-react resolve like they do for the app.
  const dir = new URL('../node_modules/.cache/partner-network-test/', import.meta.url)
  mkdirSync(fileURLToPath(dir), { recursive: true })
  const file = new URL(`PartnerNetwork-${process.pid}.mjs`, dir)
  writeFileSync(file, code)
  return import(pathToFileURL(fileURLToPath(file)).href)
}

let html
let PartnerNetwork
before(async () => {
  PartnerNetwork = (await loadComponent()).default
  html = renderToStaticMarkup(createElement(PartnerNetwork))
})

const decode = (s) => s.replace(/&amp;/g, '&').replace(/&#x27;/g, "'").replace(/&quot;/g, '"')
const hrefs = () => [...html.matchAll(/href="([^"]*)"/g)].map((m) => decode(m[1]))

test('the Partner Network section renders with its title, subtitle and disclaimer', () => {
  assert.match(html, /<section[^>]*aria-labelledby="partner-network-heading"/)
  assert.match(html, />SL Booking Partner Network</)
  assert.ok(html.includes('Professional support for your property — from trusted local partners.'))
  assert.ok(html.includes('Photography, Landscaping, Garden Maintenance and Social Media Promotion.'))
  assert.ok(decode(html).includes(
    'Partner services are provided directly by the respective service providers. SL Booking helps connect property owners with these local professional partners.'))
})

test('all three partners appear, each in its own card', () => {
  assert.equal(PARTNERS.length, 3)
  assert.equal((html.match(/data-partner-id=/g) || []).length, 3)
  for (const { name } of EXPECTED) assert.ok(decode(html).includes(name), name)
})

test('the correct phone numbers are displayed', () => {
  for (const { phone } of EXPECTED) assert.ok(html.includes(phone), phone)
})

test('WhatsApp links use wa.me with the normalised number and the encoded message', () => {
  const wa = hrefs().filter((h) => h.startsWith('https://wa.me/'))
  assert.deepEqual(wa, EXPECTED.map((p) => `https://wa.me/${p.wa}?text=${ENCODED_MESSAGE}`))
  assert.equal(
    ENCODED_MESSAGE,
    'Hello%2C%20I%20am%20a%20property%20owner%20on%20SL%20Booking.%20I%20would%20like%20to%20know%20more%20about%20your%20property%20support%20services.')
  for (const url of wa) assert.equal(new URL(url).searchParams.get('text'), PARTNER_WHATSAPP_MESSAGE)
  assert.match(html, /target="_blank" rel="noopener noreferrer"/)
})

test('Call links are tel: links in international format', () => {
  assert.deepEqual(hrefs().filter((h) => h.startsWith('tel:')), EXPECTED.map((p) => p.tel))
  assert.equal(callLink('077 960 6117'), 'tel:+94779606117')
  assert.equal(callLink('n/a'), null)
})

test('no Facebook URL is generated while none is configured', () => {
  for (const partner of PARTNERS) assert.equal(partner.facebookUrl, null, partner.name)
  assert.ok(!hrefs().some((h) => /facebook|fb\.(me|com)/i.test(h)), 'no facebook href')
  assert.doesNotMatch(html, /facebook\.com/i)
  assert.equal(hrefs().length, 6, 'only WhatsApp + Call per partner')
  // Page names are shown as plain text instead.
  assert.ok(html.includes('Pristine Moment Photography</span>'))
  assert.ok(html.includes('Southern Garden Design and Maintain</span>'))
})

test('a Facebook button appears only for an official https facebook.com URL', () => {
  const official = { ...PARTNERS[0], facebookUrl: 'https://www.facebook.com/example.page' }
  assert.equal(partnerFacebookLink(official), 'https://www.facebook.com/example.page')
  for (const bad of ['', '   ', 'http://facebook.com/x', 'https://facebook.com.evil.test/x', 'javascript:alert(1)', 'https://example.com/facebook.com/x']) {
    assert.equal(partnerFacebookLink({ facebookUrl: bad }), null, bad)
  }
  const withFacebook = renderToStaticMarkup(createElement(PartnerNetwork, { partners: [official] }))
  assert.match(withFacebook, /href="https:\/\/www\.facebook\.com\/example\.page"/)
})

test('future partners are added through configuration; an empty list renders nothing', () => {
  const extra = { ...PARTNERS[2], id: 'new-partner', name: 'New Partner', whatsapp: 'invalid', phone: 'invalid' }
  const markup = renderToStaticMarkup(createElement(PartnerNetwork, { partners: [...PARTNERS, extra] }))
  assert.equal((markup.match(/data-partner-id=/g) || []).length, 4)
  assert.ok(markup.includes('New Partner'))
  assert.equal(renderToStaticMarkup(createElement(PartnerNetwork, { partners: [] })), '')
})

test('the Owner Dashboard renders the section after its existing content, which is unchanged', () => {
  const page = readFileSync(src('app/owner/dashboard/page.tsx'), 'utf8')
  assert.match(page, /import PartnerNetwork from '@\/components\/PartnerNetwork'/)
  assert.equal((page.match(/<PartnerNetwork \/>/g) || []).length, 1)
  for (const existing of ['api.getOwnerProperties()', 'Total Properties', 'Pending Approval', 'Occupancy Rate',
    'Recent Properties', 'Quick Actions', 'Add Your First Property', '/owner/properties/manage?propertyId=']) {
    assert.ok(page.includes(existing), existing)
  }
  assert.ok(page.indexOf('<PartnerNetwork />') > page.indexOf('Quick Actions'))
  assert.ok(page.indexOf('<PartnerNetwork />') > page.indexOf('Recent Properties'))
})
