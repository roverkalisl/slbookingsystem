'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import RoomsNotApplicable from '@/components/RoomsNotApplicable'

export default function RoomsPage() {
  const [propertyId, setPropertyId] = useState<string | null>(null)
  const [property, setProperty] = useState<any>(null)
  const [rooms, setRooms] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('propertyId')
    setPropertyId(id)
    if (id) loadData(id)
  }, [])

  const loadData = async (id: string) => {
    try {
      setLoading(true)
      const [propData, roomsData] = await Promise.all([
        api.getProperty(id),
        api.getPropertyRooms(id),
      ])
      setProperty(propData)
      setRooms(roomsData)
      setError(null)
    } catch (err: any) {
      setError(err.response?.status === 404 ? 'Property not found.' : 'Unable to load rooms.')
    } finally {
      setLoading(false)
    }
  }

  // Inline pricing editor: roomId -> draft prices
  const [editingPriceId, setEditingPriceId] = useState<string | null>(null)
  const [priceDraft, setPriceDraft] = useState({ base_price: '', weekend_price: '' })
  const [savingPrice, setSavingPrice] = useState(false)
  const [priceError, setPriceError] = useState<string | null>(null)

  const handleDeleteRoom = async (roomId: string) => {
    if (!confirm('Delete this room?')) return
    try {
      await api.deleteRoom(roomId)
      setRooms(rooms.filter(r => r.id !== roomId))
    } catch (err: any) {
      alert(err.response?.data?.detail || err.response?.data?.error || 'Failed to delete room')
    }
  }

  const startEditPrice = (room: any) => {
    setEditingPriceId(room.id)
    setPriceError(null)
    setPriceDraft({
      base_price: room.pricing?.base_price ? String(room.pricing.base_price) : '',
      weekend_price: room.pricing?.weekend_price ? String(room.pricing.weekend_price) : '',
    })
  }

  const savePrice = async (roomId: string) => {
    if (savingPrice) return
    setSavingPrice(true)
    setPriceError(null)
    try {
      const pricing = await api.setRoomPricing(roomId, {
        base_price: priceDraft.base_price,
        weekend_price: priceDraft.weekend_price.trim() === '' ? null : priceDraft.weekend_price,
      })
      setRooms(current => current.map(r => (r.id === roomId ? { ...r, pricing } : r)))
      setEditingPriceId(null)
    } catch (err: any) {
      const data = err.response?.data
      setPriceError(data?.base_price?.[0] || data?.weekend_price?.[0] || data?.detail || data?.error || 'Unable to save price.')
    } finally {
      setSavingPrice(false)
    }
  }

  if (loading) return <div className="flex items-center justify-center min-h-screen"><p className="text-gray-600">Loading...</p></div>
  if (!propertyId) return <div className="mx-auto max-w-5xl"><p className="text-red-700">Property ID required.</p></div>
  if (property?.booking_mode === 'whole_property') return <RoomsNotApplicable propertyId={propertyId} />

  return (
    <div className="mx-auto max-w-5xl pb-10">
      <Link
        href={`/owner/properties/manage?propertyId=${encodeURIComponent(propertyId)}`}
        className="text-sm font-semibold text-blue-600 hover:text-blue-700"
      >
        ← Back to Property
      </Link>

      <div className="mb-8 mt-4">
        <h1 className="text-4xl font-bold text-gray-900">Room Management</h1>
        <p className="mt-2 text-gray-600">{property?.name || 'Property'}</p>
      </div>

      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}

      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-semibold">Rooms ({rooms.length})</h2>
        <Link
          href={`/owner/properties/rooms/add?propertyId=${encodeURIComponent(propertyId)}`}
          className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700"
        >
          + Add Room
        </Link>
      </div>

      <div className="space-y-4">
        {rooms.length > 0 ? (
          rooms.map(room => (
            <div key={room.id} className="rounded-lg border border-gray-200 bg-white p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-bold text-lg text-gray-900">{room.name}</h3>
                  <p className="mt-1 text-sm text-gray-600">
                    {room.room_type} • {room.max_adults} adults, {room.max_children || 0} children
                  </p>
                  <div className="mt-2 flex gap-2 text-xs text-gray-500">
                    <span>{room.number_of_beds} bed(s) ({room.bed_configuration})</span>
                    <span>•</span>
                    <span>{room.total_rooms} unit(s)</span>
                  </div>
                  <p className={`mt-2 text-sm font-semibold ${room.pricing ? 'text-gray-900' : 'text-red-600'}`}>
                    {room.pricing
                      ? `LKR ${Number(room.pricing.base_price).toLocaleString()} / night${room.pricing.weekend_price ? ` (weekend LKR ${Number(room.pricing.weekend_price).toLocaleString()})` : ''}`
                      : 'No price set - required before submitting for approval'}
                  </p>
                  {editingPriceId === room.id && (
                    <div className="mt-3 flex flex-wrap items-end gap-2">
                      <label className="text-sm text-gray-700">
                        Price per night *
                        <input
                          type="number" min="1" step="0.01" value={priceDraft.base_price}
                          onChange={e => setPriceDraft(d => ({ ...d, base_price: e.target.value }))}
                          className="mt-1 block w-36 rounded-lg border border-gray-300 px-2 py-1"
                        />
                      </label>
                      <label className="text-sm text-gray-700">
                        Weekend (optional)
                        <input
                          type="number" min="1" step="0.01" value={priceDraft.weekend_price}
                          onChange={e => setPriceDraft(d => ({ ...d, weekend_price: e.target.value }))}
                          className="mt-1 block w-36 rounded-lg border border-gray-300 px-2 py-1"
                        />
                      </label>
                      <button
                        type="button" onClick={() => savePrice(room.id)} disabled={savingPrice || !priceDraft.base_price}
                        className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        {savingPrice ? 'Saving...' : 'Save'}
                      </button>
                      <button type="button" onClick={() => setEditingPriceId(null)} className="px-2 py-1.5 text-sm text-gray-600">
                        Cancel
                      </button>
                      {priceError && <p className="w-full text-sm text-red-600">{priceError}</p>}
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Link
                    href={`/owner/properties/rooms/photos?propertyId=${encodeURIComponent(propertyId)}&roomId=${room.id}`}
                    className="px-3 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    Photos
                  </Link>
                  {/* There is no room edit page in this static export - the
                      former "Edit" link 404'd. Pricing is edited inline. */}
                  <button
                    type="button"
                    onClick={() => startEditPrice(room)}
                    className="px-3 py-2 text-sm font-medium text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                  >
                    {room.pricing ? 'Edit price' : 'Set price'}
                  </button>
                  <button
                    onClick={() => handleDeleteRoom(room.id)}
                    className="px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-lg bg-white p-8 text-center text-gray-600">
            <p className="mb-4">No rooms yet. Add your first room to get started.</p>
            <Link
              href={`/owner/properties/rooms/add?propertyId=${encodeURIComponent(propertyId)}`}
              className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium"
            >
              Add Your First Room
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
