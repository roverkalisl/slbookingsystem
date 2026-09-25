'use client'

/**
 * GA4 loader + page-view tracking for every route, including client-side
 * navigation. Renders nothing (and loads no Google script) unless
 * NEXT_PUBLIC_GA_MEASUREMENT_ID is set. Automatic page views are disabled,
 * so only the query-free pathname is ever sent (see lib/analytics.ts).
 */

import { useEffect } from 'react'
import Script from 'next/script'
import { usePathname } from 'next/navigation'
import { getMeasurementId, initAnalytics, trackPageView } from '@/lib/analytics'

export function GoogleAnalytics() {
  const measurementId = getMeasurementId()
  const pathname = usePathname()

  useEffect(() => {
    if (!measurementId || !pathname) return
    initAnalytics() // queue is ready before the first page view, even if gtag.js is still loading
    trackPageView(pathname)
  }, [measurementId, pathname])

  if (!measurementId) return null
  return <Script src={`https://www.googletagmanager.com/gtag/js?id=${measurementId}`} strategy="afterInteractive" />
}
