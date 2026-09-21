'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'

interface RoomPhoto {
  id: string
  cloudinary_url: string
  is_cover: boolean
  display_order: number
}

export default function RoomPhotosPage() {
  const [params, setParams] = useState({ propertyId: '', roomId: '' })
  const [room, setRoom] = useState<any>(null)
  const [photos, setPhotos] = useState<RoomPhoto[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [photoError, setPhotoError] = useState<string | null>(null)
  const [photoSuccess, setPhotoSuccess] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const propertyId = params.get('propertyId') || ''
    const roomId = params.get('roomId') || ''
    setParams({ propertyId, roomId })
    if (propertyId && roomId) loadData(propertyId, roomId)
  }, [])

  const loadData = async (propertyId: string, roomId: string) => {
    try {
      setLoading(true)
      // Get property to verify ownership, then get room
      const property = await api.getProperty(propertyId)
      const rooms = await api.getPropertyRooms(propertyId)
      const foundRoom = rooms.find((r: any) => r.id === roomId)

      if (!foundRoom) throw new Error('Room not found')

      setRoom(foundRoom)
      if (foundRoom.photos) {
        const mapped = foundRoom.photos.map((p: any) => ({
          id: p.id,
          cloudinary_url: p.cloudinary_url,
          is_cover: p.is_cover,
          display_order: p.display_order,
        }))
        setPhotos(mapped)
      }
      setError(null)
    } catch (err: any) {
      setError('Unable to load room photos.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeletePhoto = async (photoId: string) => {
    if (!confirm('Delete this photo?')) return
    try {
      setPhotoError(null)
      await api.deleteRoomPhoto(params.roomId, photoId)
      setPhotos(photos.filter(p => p.id !== photoId))
      setPhotoSuccess('Photo deleted successfully')
    } catch (err: any) {
      setPhotoError('Failed to delete photo')
    }
  }

  if (loading) return <div className="flex items-center justify-center min-h-screen"><p className="text-gray-600">Loading...</p></div>

  return (
    <div className="mx-auto max-w-5xl pb-10">
      <Link
        href={`/owner/properties/rooms?propertyId=${encodeURIComponent(params.propertyId)}`}
        className="text-sm font-semibold text-blue-600 hover:text-blue-700"
      >
        ← Back to Rooms
      </Link>

      <div className="mb-8 mt-4">
        <h1 className="text-4xl font-bold text-gray-900">Room Photos</h1>
        <p className="mt-2 text-gray-600">{room?.name || 'Room'}</p>
      </div>

      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}

      <section className="rounded-lg bg-white p-6 shadow">
        <h2 className="text-xl font-semibold">Photos for {room?.name}</h2>
        <p className="mt-2 text-sm text-gray-600">{photos.length} photo(s) uploaded (unlimited)</p>

        {photoError && <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">{photoError}</div>}
        {photoSuccess && <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-3 text-green-800">{photoSuccess}</div>}

        {photos.length > 0 ? (
          <div className="mt-6 grid gap-4 sm:grid-cols-2 md:grid-cols-3">
            {photos.map(photo => (
              <div key={photo.id} className="relative">
                <img src={photo.cloudinary_url} alt={room?.name} className="h-40 w-full rounded-lg object-cover" />
                {photo.is_cover && <span className="absolute top-2 left-2 rounded bg-blue-600 px-2 py-1 text-xs text-white">Cover</span>}
                <button
                  onClick={() => handleDeletePhoto(photo.id)}
                  className="mt-2 w-full rounded bg-red-50 px-3 py-2 text-sm text-red-600 hover:bg-red-100"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-6 rounded-lg bg-gray-50 p-8 text-center text-gray-600">
            <p>No photos yet for this room.</p>
            <p className="mt-2 text-sm">Upload photos via Cloudinary.</p>
          </div>
        )}

        <p className="mt-6 text-sm text-gray-500">
          Room photos are separate from property photos. Each room can have unlimited photos.
        </p>
      </section>
    </div>
  )
}
