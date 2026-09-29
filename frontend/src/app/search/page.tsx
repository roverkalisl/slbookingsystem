/**
 * Search page - Server Component carrying the page metadata; the UI lives in
 * the client component search-ui.tsx. Filtered URLs (/search?destination=...)
 * get "X-Robots-Tag: noindex, follow" from Django; their canonical is /search.
 */

import { pageMetadata } from '@/lib/seo'
import SearchPage from './search-ui'

export const metadata = pageMetadata({
  title: 'Search Accommodation in Sri Lanka',
  description: 'Search villas, hotels, guest houses and holiday homes across Sri Lanka by destination, dates and number of guests.',
  path: '/search',
})

export default function SearchRoute() {
  return <SearchPage />
}
