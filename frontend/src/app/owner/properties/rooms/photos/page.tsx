'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import RoomsNotApplicable from '@/components/RoomsNotApplicable'

interface RoomPhoto {
  id: string
  cloudinary_url: string
  is_cover: boolean
  display_order: number
}

const MAX_PHOTO_SIZE_MB = 10
// Each room needs 1-5 photos (the backend enforces the maximum on upload
// and the minimum at submit-for-approval).
const MAX_ROOM_PHOTOS = 5
const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

export default function RoomPhotosPage() {
  const [params, setParams] = useState({ propertyId: '', roomId: '' })
  const [room, setRoom] = useState<any>(null)
  const [photos, setPhotos] = useState<RoomPhoto[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [photoError, setPhotoError] = useState<string | null>(null)
  const [photoSuccess, setPhotoSuccess] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{ done: number; total: number } | null>(null)
  const [isVilla, setIsVilla] = useState(false)

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
      // Owner-only property load (404 for another owner's property), then the room
      const property = await api.getOwnedProperty(propertyId)
      if (property.booking_mode === 'whole_property') {
        // Entry Villa: no rooms - its property photos are the villa's gallery
        setIsVilla(true)
        return
      }
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

  const handleUploadPhotos = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return
    const files = Array.from(fileList)

    setPhotoError(null)
    setPhotoSuccess(null)

    const invalid = files.find(f => !ACCEPTED_IMAGE_TYPES.includes(f.type))
    if (invalid) {
      setPhotoError(`"${invalid.name}" is not a supported image type (use JPEG, PNG, or WebP).`)
      return
    }
    const tooBig = files.find(f => f.size > MAX_PHOTO_SIZE_MB * 1024 * 1024)
    if (tooBig) {
      setPhotoError(`"${tooBig.name}" is larger than ${MAX_PHOTO_SIZE_MB}MB.`)
      return
    }
    // Max 5 per room (the backend enforces this too - this just avoids a
    // partial upload). Nothing is uploaded if the selection doesn't fit.
    const remaining = MAX_ROOM_PHOTOS - photos.length
    if (files.length > remaining) {
      setPhotoError(
        remaining > 0
          ? `A room can have at most ${MAX_ROOM_PHOTOS} photos. You can add ${remaining} more - you selected ${files.length}.`
          : `This room already has ${MAX_ROOM_PHOTOS} photos. Delete a photo before uploading another.`
      )
      return
    }

    setUploading(true)
    setUploadProgress({ done: 0, total: files.length })
    let uploadedCount = 0
    try {
      for (const file of files) {
        const result = await api.uploadPhoto(
          file,
          () => api.getRoomUploadSignature(params.roomId),
          (data) => api.addRoomPhoto(params.roomId, data)
        )
        setPhotos(current => [...current, {
          id: result.id,
          cloudinary_url: result.cloudinary_url,
          is_cover: result.is_cover,
          display_order: result.display_order,
        }])
        uploadedCount += 1
        setUploadProgress({ done: uploadedCount, total: files.length })
      }
      setPhotoSuccess(`${uploadedCount} photo(s) uploaded successfully.`)
    } catch (err: any) {
      const reason = err.response?.data?.error || err.message || 'upload failed'
      setPhotoError(
        uploadedCount > 0
          ? `Uploaded ${uploadedCount} of ${files.length} photo(s) before an error: ${reason}`
          : (err.response?.data?.error || err.message || 'Upload failed. Please try again.')
      )
    } finally {
      setUploading(false)
      setUploadProgress(null)
    }
  }

  const roomIsFull = photos.length >= MAX_ROOM_PHOTOS

  if (loading) return <div className="flex items-center justify-center min-h-screen"><p className="text-gray-600">Loading...</p></div>
  if (isVilla) return <RoomsNotApplicable propertyId={params.propertyId} />

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
        <p className="mt-2 text-sm text-gray-600">
          Upload 1–{MAX_ROOM_PHOTOS} room photos · <span className="font-semibold">{photos.length} / {MAX_ROOM_PHOTOS} photos</span>
        </p>

        {photoError && <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">{photoError}</div>}
        {photoSuccess && <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-3 text-green-800">{photoSuccess}</div>}

        <label
          className={`mt-6 flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 p-8 text-center transition-colors ${
            roomIsFull ? 'cursor-not-allowed opacity-60' : 'cursor-pointer hover:border-blue-400 hover:bg-blue-50'
          }`}
        >
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            className="hidden"
            disabled={uploading || roomIsFull}
            onChange={(e) => { handleUploadPhotos(e.target.files); e.target.value = '' }}
          />
          {uploading ? (
            <p className="text-sm text-gray-600">Uploading {uploadProgress?.done ?? 0} of {uploadProgress?.total ?? 0}...</p>
          ) : roomIsFull ? (
            <p className="font-medium text-gray-700">
              Maximum of {MAX_ROOM_PHOTOS} photos reached - delete a photo to upload another.
            </p>
          ) : (
            <>
              <p className="font-medium text-gray-700">Click to upload room photos</p>
              <p className="text-xs text-gray-500">JPEG, PNG, or WebP - up to {MAX_PHOTO_SIZE_MB}MB each - select multiple at once</p>
            </>
          )}
        </label>

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
            <p>No photos yet for this room. Upload your first one above.</p>
          </div>
        )}

        <p className="mt-6 text-sm text-gray-500">
          Room photos are separate from property photos. Each room needs 1–{MAX_ROOM_PHOTOS} photos.
        </p>
      </section>
    </div>
  )
}
