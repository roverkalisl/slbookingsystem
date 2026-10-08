/**
 * Root layout for the application
 */

import type { Metadata } from 'next'
import Link from 'next/link'
import { Navbar } from '@/components/Navbar'
import { AuthInitializer } from '@/components/AuthInitializer'
import { FloatingBookingAssistant } from '@/components/FloatingBookingAssistant'
import { GoogleAnalytics } from '@/components/GoogleAnalytics'
import { AdSense } from '@/components/AdSense'
import { getAdSenseClient } from '@/lib/adsense'
import {
  CANONICAL_SITE_URL, DEFAULT_DESCRIPTION, DEFAULT_OPEN_GRAPH, DEFAULT_TITLE, DEFAULT_TWITTER, SITE_NAME,
} from '@/lib/seo'
import './globals.css'

const adSenseClient = getAdSenseClient()

export const metadata: Metadata = {
  // Absolute URLs (Open Graph image, canonicals) resolve against the canonical public site
  metadataBase: new URL(CANONICAL_SITE_URL),
  title: DEFAULT_TITLE,
  description: DEFAULT_DESCRIPTION,
  keywords: ['accommodation', 'booking', 'Sri Lanka', 'hotels', 'villas', 'apartments'],
  authors: [{ name: 'SL Booking' }],
  // Site-wide social defaults (the home, search and property pages get page-specific
  // tags from Django; property pages use their real cover photo instead of this image)
  openGraph: DEFAULT_OPEN_GRAPH,
  twitter: DEFAULT_TWITTER,
  // SL Booking mark (the navbar's house icon in brand blue) - frontend/public
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: '16x16 32x32 48x48' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    apple: [{ url: '/apple-icon.png', sizes: '180x180', type: 'image/png' }],
  },
  // Google Search Console ownership (https://slbooking.hotel.lk/) - renders
  // <meta name="google-site-verification" content="..."> in every page <head>
  verification: {
    google: 'NcV_FHp_ZSu_JRVERF8FNny1CMceMW5TVW7xmqQaTHI',
  },
  // AdSense site ownership: <meta name="google-adsense-account" content="ca-pub-..."> in every
  // page <head>. This is only the account tag - the ads script itself loads on public pages only.
  ...(adSenseClient ? { other: { 'google-adsense-account': adSenseClient } } : {}),
}

const FOOTER_LINKS = [
  { href: '/about', label: 'About' },
  { href: '/contact', label: 'Contact' },
  { href: '/privacy', label: 'Privacy Policy' },
  { href: '/terms', label: 'Terms of Service' },
]

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50">
        {/* GA4 - renders nothing unless NEXT_PUBLIC_GA_MEASUREMENT_ID is set */}
        <GoogleAnalytics />
        {/* Google AdSense Auto Ads - public pages only, loaded once (renders nothing unless configured) */}
        <AdSense />
        <AuthInitializer />
        <Navbar />
        <main className="min-h-screen">
          {children}
        </main>
        <FloatingBookingAssistant />
        <footer className="bg-gray-900 text-white mt-16 py-8">
          <div className="max-w-7xl mx-auto px-4 text-center">
            <nav aria-label="Footer" className="mb-4 flex flex-wrap justify-center gap-x-6 gap-y-2 text-sm text-gray-300">
              {FOOTER_LINKS.map((link) => (
                <Link key={link.href} href={link.href} className="hover:text-white">
                  {link.label}
                </Link>
              ))}
            </nav>
            <p>&copy; 2026 SL Booking. All rights reserved.</p>
          </div>
        </footer>
      </body>
    </html>
  )
}
