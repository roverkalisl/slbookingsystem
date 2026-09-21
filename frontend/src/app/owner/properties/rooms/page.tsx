'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'

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

  const handleDeleteRoom = async (roomId: string) => {
    if (!confirm('Delete this room?')) return
    try {
      // TODO: Add delete room endpoint if needed
      // For now, handle via backend
      setRooms(rooms.filter(r => r.id !== roomId))
    } catch (err) {
      alert('Failed to delete room')
    }
  }

  if (loading) return <div className="flex items-center justify-center min-h-screen"><p className="text-gray-600">Loading...</p></div>
  if (!propertyId) return <div className="mx-auto max-w-5xl"><p className="text-red-700">Property ID required.</p></div>

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
                </div>
                <div className="flex gap-2">
                  <Link
                    href={`/owner/properties/rooms/photos?propertyId=${encodeURIComponent(propertyId)}&roomId=${room.id}`}
                    className="px-3 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                  >
                    Photos
                  </Link>
                  <Link
                    href={`/owner/properties/rooms/edit?propertyId=${encodeURIComponent(propertyId)}&roomId=${room.id}`}
                    className="px-3 py-2 text-sm font-medium text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                  >
                    Edit
                  </Link>
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
