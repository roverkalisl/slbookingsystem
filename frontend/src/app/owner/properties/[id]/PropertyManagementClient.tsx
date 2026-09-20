'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export default function PropertyManagementClient({ propertyId }: { propertyId: string }) {
  const [property, setProperty] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getProperty(propertyId).then(setProperty).catch((requestError: any) => {
      setError(requestError.response?.status === 404 ? 'Property not found.' : 'Unable to load this property.')
    })
  }, [propertyId])

  return <div className="mx-auto max-w-6xl">{error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}{!property && !error && <p className="text-gray-600">Loading property...</p>}{property && <><div className="mb-8 flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm uppercase tracking-wide text-blue-700">Manage property</p><h1 className="mt-2 text-4xl font-bold text-gray-900">{property.name}</h1><p className="mt-2 text-gray-600">{property.city}, {property.district}</p></div><span className="rounded-full bg-gray-100 px-3 py-1 text-sm font-semibold">{String(property.status).replace('_', ' ').toUpperCase()}</span></div><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><Link href={`/owner/properties/${propertyId}/rooms`} className="rounded-lg bg-white p-5 shadow hover:ring-2 hover:ring-blue-500"><strong>Rooms</strong><p className="mt-2 text-sm text-gray-600">Add rooms and manage capacity.</p></Link><div className="rounded-lg bg-white p-5 shadow"><strong>Photos</strong><p className="mt-2 text-sm text-gray-600">{property.photos?.length || 0} of 5 property photos.</p></div><div className="rounded-lg bg-white p-5 shadow"><strong>Pricing</strong><p className="mt-2 text-sm text-gray-600">Configure pricing per room.</p></div><div className="rounded-lg bg-white p-5 shadow"><strong>Approval</strong><p className="mt-2 text-sm text-gray-600">Complete property, rooms, and pricing first.</p></div></div><section className="mt-6 rounded-lg bg-white p-6 shadow"><h2 className="text-xl font-semibold">Overview</h2><p className="mt-3 whitespace-pre-wrap text-gray-700">{property.description}</p><dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="font-semibold">Address</dt><dd>{property.address}, {property.city}</dd></div><div><dt className="font-semibold">House rules</dt><dd>{property.house_rules || 'Not provided'}</dd></div></dl></section></>}</div>
}
