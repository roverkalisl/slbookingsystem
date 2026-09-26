/**
 * Root layout for the application
 */

import type { Metadata } from 'next'
import { Navbar } from '@/components/Navbar'
import { AuthInitializer } from '@/components/AuthInitializer'
import { GoogleAnalytics } from '@/components/GoogleAnalytics'
import { AdSense } from '@/components/AdSense'
import { getAdSenseClient } from '@/lib/adsense'
import './globals.css'

const adSenseClient = getAdSenseClient()

export const metadata: Metadata = {
  title: 'SL Booking - Sri Lankan Accommodation Marketplace',
  description: 'Book accommodations across Sri Lanka - Villas, Apartments, Resorts',
  keywords: ['accommodation', 'booking', 'Sri Lanka', 'hotels', 'villas', 'apartments'],
  authors: [{ name: 'SL Booking' }],
  // Google Search Console ownership (https://slbooking.hotel.lk/) - renders
  // <meta name="google-site-verification" content="..."> in every page <head>
  verification: {
    google: 'NcV_FHp_ZSu_JRVERF8FNny1CMceMW5TVW7xmqQaTHI',
  },
  // AdSense site ownership: <meta name="google-adsense-account" content="ca-pub-..."> in every
  // page <head>. This is only the account tag - the ads script itself loads on public pages only.
  ...(adSenseClient ? { other: { 'google-adsense-account': adSenseClient } } : {}),
}

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
        <footer className="bg-gray-900 text-white mt-16 py-8">
          <div className="max-w-7xl mx-auto px-4 text-center">
            <p>&copy; 2026 SL Booking. All rights reserved.</p>
          </div>
        </footer>
      </body>
    </html>
  )
}
