/**
 * Property details page - Server Component
 * Enables static export with generateStaticParams
 * UI logic in separate Client Component (property-content.tsx)
 */

import { Suspense } from 'react'
import { PropertyContent } from './property-ui'

export default function PropertyPage() {
  return (
    <Suspense fallback={<div className="text-center py-12">Loading...</div>}>
      <PropertyContent />
    </Suspense>
  )
}

// Required for static export: generateStaticParams() in Server Component
// Property pages are loaded client-side from API at runtime
// Pre-generate a fallback route (users access properties via search/API)
export async function generateStaticParams() {
  // Return a dummy ID to satisfy static export requirement
  // Real property data loads client-side from /api/properties/{id}
  return [
    { id: '0' }, // Fallback route (won't be accessed in normal flow)
  ]
}
