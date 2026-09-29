/**
 * Site-wide SEO defaults for the Next.js metadata API.
 *
 * Canonical public site: https://slbooking.hotel.lk (NOT the Render URL, and
 * NOT NEXT_PUBLIC_SITE_URL - that one is the Stripe return address).
 * Page-specific tags for the home, search and property pages are written by
 * Django when it serves them (backend/config/seo.py); static pages such as
 * /about use pageMetadata() below.
 */

import type { Metadata } from 'next'

export const SITE_NAME = 'SL Booking'
export const CANONICAL_SITE_URL = (process.env.NEXT_PUBLIC_CANONICAL_SITE_URL || 'https://slbooking.hotel.lk').replace(/\/+$/, '')
export const DEFAULT_TITLE = 'SL Booking - Sri Lankan Accommodation Marketplace'
export const DEFAULT_DESCRIPTION = 'Book accommodations across Sri Lanka - Villas, Apartments, Resorts'

/** Default social image (frontend/public/og-default.png, 1200x630) - property pages use their own cover photo. */
export const DEFAULT_OG_IMAGE = {
  url: '/og-default.png',
  width: 1200,
  height: 630,
  alt: 'SL Booking - villas, hotels, guest houses & holiday homes across Sri Lanka',
}

export const DEFAULT_OPEN_GRAPH: NonNullable<Metadata['openGraph']> = {
  type: 'website',
  siteName: SITE_NAME,
  title: DEFAULT_TITLE,
  description: DEFAULT_DESCRIPTION,
  images: [DEFAULT_OG_IMAGE],
}

export const DEFAULT_TWITTER: NonNullable<Metadata['twitter']> = {
  card: 'summary_large_image',
  title: DEFAULT_TITLE,
  description: DEFAULT_DESCRIPTION,
  images: [DEFAULT_OG_IMAGE.url],
}

/**
 * Metadata for a static public page: title (with the " | SL Booking" template),
 * description, canonical URL and matching Open Graph / Twitter tags.
 * (Next.js replaces - not merges - openGraph/twitter objects, so the defaults
 * are repeated here to keep the default image.)
 */
export function pageMetadata({ title, description, path, fullTitle: titleOverride }: {
  title: string
  description: string
  path: string
  /** Use this exact title instead of "<title> | SL Booking" (e.g. the home page) */
  fullTitle?: string
}): Metadata {
  const fullTitle = titleOverride || `${title} | ${SITE_NAME}`
  return {
    title: fullTitle,
    description,
    // Resolved against metadataBase (the root renders as https://slbooking.hotel.lk - the same URL as ".../")
    alternates: { canonical: path },
    openGraph: { ...DEFAULT_OPEN_GRAPH, title: fullTitle, description, url: path },
    twitter: { ...DEFAULT_TWITTER, title: fullTitle, description },
  }
}
