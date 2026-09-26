'use client'

/**
 * Google AdSense Auto Ads - the official adsbygoogle.js script, loaded with
 * next/script from the root layout, on PUBLIC pages only (homepage, search,
 * property pages, informational pages). Never on admin, owner, login/
 * register, the guest's bookings/payment page, or noindex pages such as 404.
 *
 * - Loads once: one <Script> with a fixed id in the root layout; next/script
 *   never injects the same id twice, and the layout persists across
 *   client-side navigation.
 * - Eligibility is decided in the browser after mount (the 404 page can only
 *   be recognised there), so nothing AdSense-related is in the static HTML.
 * - Arriving on a private page via client-side navigation while the script is
 *   already loaded reloads that page once, so it is shown without ads.
 * - Renders nothing when NEXT_PUBLIC_ADSENSE_PUBLISHER_ID is not configured.
 */

import { useEffect, useState } from 'react'
import Script from 'next/script'
import { usePathname } from 'next/navigation'
import { getAdSenseScriptSrc, isNoIndexPage, isPrivatePath, needsAdFreeReload } from '@/lib/adsense'

export function AdSense() {
  const pathname = usePathname()
  const src = getAdSenseScriptSrc()
  const [eligible, setEligible] = useState(false)

  useEffect(() => {
    if (needsAdFreeReload(pathname, document)) {
      window.location.reload()
      return
    }
    setEligible(!!src && !isPrivatePath(pathname) && !isNoIndexPage(document))
  }, [pathname, src])

  if (!src || !eligible) return null
  return <Script id="google-adsense" src={src} strategy="afterInteractive" crossOrigin="anonymous" />
}
