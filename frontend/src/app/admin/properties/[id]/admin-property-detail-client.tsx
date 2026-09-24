'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/lib/api'
import { useDynamicRouteId } from '@/lib/useDynamicRouteId'
import type { Property } from '@/types'
import { ArrowLeft, CheckCircle2, XCircle, Loader2 } from 'lucide-react'

export default function AdminPropertyDetailClient({ propertyId: paramId }: { propertyId: string }) {
  const router = useRouter()
  // Real id from the URL - the static export pre-renders this page with '0'
  const propertyId = useDynamicRouteId(paramId)
  const [property, setProperty] = useState<Property | null>(null)
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState<'approve' | 'reject' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [rejectionReason, setRejectionReason] = useState('')

  useEffect(() => {
    if (!propertyId) return
    const loadProperty = async () => {
      try {
        // Detail endpoint (admins see every status) - includes photos and
        // rooms for review. The old version scanned only the first page of
        // the property list, so later properties showed "not found".
        setProperty(await api.getProperty(propertyId))
      } catch (err: any) {
        setError(err.response?.status === 404 ? 'Property not found' : 'Failed to load property')
      } finally {
        setLoading(false)
      }
    }
    loadProperty()
  }, [propertyId])

  const approve = async () => {
    if (!property) return
    try {
      setAction('approve')
      await api.approveProperty(property.id)
      router.push('/admin/properties?status=approved')
    } catch (err: any) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Failed to approve property')
      setAction(null)
    }
  }

  const reject = async () => {
    if (!property || !rejectionReason.trim()) {
      setError('Please provide a rejection reason')
      return
    }
    try {
      setAction('reject')
      await api.rejectProperty(property.id, rejectionReason)
      router.push('/admin/properties?status=rejected')
    } catch (err: any) {
      setError(err.response?.data?.error || err.response?.data?.detail || 'Failed to reject property')
      setAction(null)
    }
  }

  const rooms: any[] = (property as any)?.room_types || []
  // Entry Villa (whole property): show the villa itself, not an owner-managed room
  const isVilla = (property as any)?.booking_mode === 'whole_property'
  const villaUnit: any = isVilla ? rooms.find((room) => room.is_property_unit) || null : null

  if (loading) return <div className="py-12 text-center text-gray-600">Loading property details...</div>
  if (!property) return <div className="py-12 text-center text-red-700">{error || 'Property not found'}</div>

  return (
    <div>
      <Link href="/admin/properties" className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to Properties
      </Link>
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h1 className="text-3xl font-bold text-gray-900">{property.name}</h1>
        <p className="text-gray-600 mt-2">{property.short_description}</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div><p className="text-sm text-gray-600">Status</p><p className="font-semibold mt-1">{property.status}</p></div>
          <div><p className="text-sm text-gray-600">City</p><p className="font-semibold mt-1">{property.city}</p></div>
          <div><p className="text-sm text-gray-600">Bedrooms</p><p className="font-semibold mt-1">{property.bedrooms}</p></div>
          <div><p className="text-sm text-gray-600">Guests</p><p className="font-semibold mt-1">{property.max_guests}</p></div>
        </div>
      </div>
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-bold mb-3">Photos ({property.photos.length})</h2>
        {property.photos.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {/* Cover photo first and clearly marked */}
            {[...property.photos].sort((a: any, b: any) => Number(!!b.is_cover) - Number(!!a.is_cover)).map((photo: any) => (
              <div key={photo.id} className={`relative rounded ${photo.is_cover ? 'ring-2 ring-blue-600' : ''}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={photo.url} alt={property.name} className="h-32 w-full rounded object-cover" />
                {photo.is_cover && <span className="absolute top-2 left-2 rounded bg-blue-600 px-2 py-1 text-xs font-semibold text-white">Cover photo</span>}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-600">No property photos.</p>
        )}
      </div>
      {isVilla ? (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-bold mb-3">Entire Villa</h2>
        {villaUnit ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><p className="text-gray-600">Capacity</p><p className="font-semibold mt-1">{villaUnit.max_adults} adults, {villaUnit.max_children || 0} children (max {villaUnit.total_occupancy} guests)</p></div>
            <div><p className="text-gray-600">Beds &amp; bathroom</p><p className="font-semibold mt-1">{villaUnit.number_of_beds} {villaUnit.bed_configuration} bed(s) • {String(villaUnit.bathroom_type || '').replace('_', ' ')} bathroom</p></div>
            <div><p className="text-gray-600">Price</p><p className="font-semibold mt-1">
              {villaUnit.pricing
                ? `LKR ${Number(villaUnit.pricing.base_price).toLocaleString()} / night${villaUnit.pricing.weekend_price ? ` (weekend LKR ${Number(villaUnit.pricing.weekend_price).toLocaleString()})` : ''}`
                : 'no price set'}
            </p></div>
            <div><p className="text-gray-600">Availability</p><p className="font-semibold mt-1">{villaUnit.is_active && villaUnit.total_rooms === 1 ? 'Bookable as 1 unit (owner-blocked dates excluded)' : 'Not configured'}</p></div>
          </div>
        ) : (
          <p className="text-sm text-red-600">Villa details have not been set.</p>
        )}
        <p className="mt-3 text-xs text-gray-500">Entry Villa is booked as a whole - the property photos above are the villa&apos;s gallery.</p>
      </div>
      ) : (
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-bold mb-3">Rooms ({rooms.length})</h2>
        {rooms.length > 0 ? (
          <div className="space-y-4">
            {rooms.map((room) => (
              <div key={room.id} className="border-t pt-4 first:border-t-0 first:pt-0">
                <p className="font-semibold">{room.name} {room.is_active === false && <span className="text-sm text-gray-500">(inactive)</span>}</p>
                <p className="text-sm text-gray-600">
                  {room.max_adults} adults, {room.max_children || 0} children • {room.total_rooms} unit(s) •{' '}
                  {room.pricing
                    ? `LKR ${Number(room.pricing.base_price).toLocaleString()} / night${room.pricing.weekend_price ? ` (weekend LKR ${Number(room.pricing.weekend_price).toLocaleString()})` : ''}`
                    : 'no price set'}
                </p>
                {room.photos?.length > 0 ? (
                  <div className="mt-2 grid grid-cols-3 md:grid-cols-6 gap-2">
                    {room.photos.map((photo: any) => (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img key={photo.id} src={photo.cloudinary_url} alt={room.name} className="h-20 w-full rounded object-cover" />
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-600 mt-1">No room photos.</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-600">No rooms.</p>
        )}
      </div>
      )}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-3">Description</h2>
        <p className="text-gray-700 whitespace-pre-line">{property.description}</p>
        {error && <p className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {property.status === 'pending_approval' && (
          <div className="mt-6 space-y-3 border-t pt-6">
            <button onClick={approve} disabled={Boolean(action)} className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-3 font-medium text-white disabled:opacity-50">
              {action === 'approve' ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Approve Property
            </button>
            <textarea value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} rows={3} placeholder="Rejection reason" className="w-full rounded-lg border border-gray-300 p-3" />
            <button onClick={reject} disabled={Boolean(action)} className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-3 font-medium text-white disabled:opacity-50">
              {action === 'reject' ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />} Reject Property
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
