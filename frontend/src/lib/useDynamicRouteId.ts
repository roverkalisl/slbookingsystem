'use client'

import { useEffect, useState } from 'react'

/**
 * Real id for a dynamic [id] route in the static export.
 *
 * `output: 'export'` pre-renders each [id] page once with the placeholder id
 * '0' (generateStaticParams), and Django serves that shell for every real id
 * (config/urls.py FRONTEND_DYNAMIC_ROUTES). useParams() therefore returns the
 * placeholder, so the real id is read from the browser URL's last segment.
 * Returns null until mounted.
 */
export function useDynamicRouteId(paramId?: string): string | null {
  const [id, setId] = useState<string | null>(null)

  useEffect(() => {
    const last = window.location.pathname.replace(/\/+$/, '').split('/').pop()
    if (last && last !== '0') {
      setId(decodeURIComponent(last))
    } else {
      setId(paramId && paramId !== '0' ? paramId : null)
    }
  }, [paramId])

  return id
}
