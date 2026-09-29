/**
 * Home page - Server Component carrying the page metadata; the UI lives in
 * the client component home-ui.tsx (same pattern as property/[id]).
 */

import { pageMetadata } from '@/lib/seo'
import Home from './home-ui'

export const metadata = pageMetadata({
  title: 'Home',
  fullTitle: 'SL Booking | Villas, Hotels & Holiday Homes in Sri Lanka',
  description: 'Search and book villas, hotels, guest houses and holiday homes across Sri Lanka. '
    + 'Compare photos, amenities and prices, and book your stay with SL Booking.',
  path: '/',
})

export default function HomePage() {
  return <Home />
}
