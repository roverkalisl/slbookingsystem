'use client'

import { useEffect, useState } from 'react'
import PropertyManagementClient from '../[id]/PropertyManagementClient'

export default function ManagePropertyPage() {
  const [propertyId, setPropertyId] = useState<string | null>(null)

  useEffect(() => {
    setPropertyId(new URLSearchParams(window.location.search).get('propertyId'))
  }, [])

  if (propertyId === null) {
    return <p className="text-gray-600">Loading property...</p>
  }

  if (!propertyId) {
    return <p className="text-red-700">A property ID is required.</p>
  }

  return <PropertyManagementClient propertyId={propertyId} />
}