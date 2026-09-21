'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

interface Photo {
  id: string
  cloudinary_url: string
  cloudinary_public_id?: string
  is_cover: boolean
  display_order: number
}

export default function PropertyManagementClient({ propertyId }: { propertyId: string }) {
  const [property, setProperty] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [photos, setPhotos] = useState<Photo[]>([])
  const [photoError, setPhotoError] = useState<string | null>(null)
  const [photoSuccess, setPhotoSuccess] = useState<string | null>(null)

  useEffect(() => {
    loadProperty()
  }, [propertyId])

  const loadProperty = async () => {
    try {
      const data = await api.getProperty(propertyId)
      setProperty(data)
      if (data.photos) {
        const mappedPhotos = data.photos.map((p: any) => ({
          id: p.id,
          cloudinary_url: p.cloudinary_url,
          cloudinary_public_id: p.cloudinary_public_id,
          is_cover: p.is_cover,
          display_order: p.display_order,
        }))
        setPhotos(mappedPhotos)
      }
    } catch (requestError: any) {
      setError(requestError.response?.status === 404 ? 'Property not found.' : 'Unable to load this property.')
    }
  }

  const handleDeletePhoto = async (photoId: string) => {
    if (!confirm('Delete this photo?')) return
    try {
      setPhotoError(null)
      await api.deletePropertyPhoto(propertyId, photoId)
      setPhotos(photos.filter(p => p.id !== photoId))
      setPhotoSuccess('Photo deleted successfully')
    } catch (err: any) {
      setPhotoError('Failed to delete photo')
    }
  }

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'photos', label: 'Photos' },
    { id: 'rooms', label: 'Rooms' },
    { id: 'house-rules', label: 'House Rules' },
    { id: 'nearby', label: 'Nearby Places' },
    { id: 'approval', label: 'Submit for Approval' },
  ]

  return (
    <div className="mx-auto max-w-6xl pb-10">
      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}
      {!property && !error && <p className="text-gray-600">Loading property...</p>}
      {property && (
        <>
          <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-wide text-blue-700">Manage property</p>
              <h1 className="mt-2 text-4xl font-bold text-gray-900">{property.name}</h1>
              <p className="mt-2 text-gray-600">{property.city}, {property.district}</p>
            </div>
            <span className="rounded-full bg-gray-100 px-3 py-1 text-sm font-semibold">{String(property.status).replace('_', ' ').toUpperCase()}</span>
          </div>

          {/* Tabs */}
          <div className="mb-6 flex border-b border-gray-200">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-b-2 border-blue-600 text-blue-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <section className="rounded-lg bg-white p-6 shadow">
              <h2 className="text-xl font-semibold">Property Overview</h2>
              <p className="mt-3 whitespace-pre-wrap text-gray-700">{property.description}</p>
              <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <div><dt className="font-semibold">Address</dt><dd>{property.address}, {property.city}</dd></div>
                <div><dt className="font-semibold">Type</dt><dd>{property.property_type?.name || 'Not set'}</dd></div>
                <div><dt className="font-semibold">Contact</dt><dd>{property.contact_phone || property.contact_email || 'Not provided'}</dd></div>
              </dl>
            </section>
          )}

          {/* Photos Tab */}
          {activeTab === 'photos' && (
            <section className="rounded-lg bg-white p-6 shadow">
              <h2 className="text-xl font-semibold">Property Photos</h2>
              <p className="mt-2 text-sm text-gray-600">{photos.length} of 5 photos uploaded</p>
              {photoError && <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">{photoError}</div>}
              {photoSuccess && <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-3 text-green-800">{photoSuccess}</div>}
              <div className="mt-6 grid gap-4 sm:grid-cols-2 md:grid-cols-3">
                {photos.map(photo => (
                  <div key={photo.id} className="relative">
                    <img src={photo.cloudinary_url} alt="property" className="h-40 w-full rounded-lg object-cover" />
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
              {photos.length < 5 && <p className="mt-6 text-sm text-gray-600">Upload photos via the property creation wizard or Cloudinary.</p>}
            </section>
          )}

          {/* Rooms Tab */}
          {activeTab === 'rooms' && (
            <section className="rounded-lg bg-white p-6 shadow">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold">Room Types</h2>
                  <p className="mt-2 text-sm text-gray-600">{property.room_types?.length || 0} room types configured</p>
                </div>
                <Link href={`/owner/properties/${propertyId}/rooms`} className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">
                  Manage Rooms
                </Link>
              </div>
              {property.room_types && property.room_types.length > 0 && (
                <div className="mt-4 space-y-2">
                  {property.room_types.map((room: any) => (
                    <div key={room.id} className="rounded border border-gray-200 p-3">
                      <h3 className="font-semibold">{room.name}</h3>
                      <p className="text-sm text-gray-600">{room.room_type} • {room.max_adults} adults max</p>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* House Rules Tab */}
          {activeTab === 'house-rules' && (
            <section className="rounded-lg bg-white p-6 shadow">
              <h2 className="text-xl font-semibold">House Rules</h2>
              <p className="mt-3 whitespace-pre-wrap text-gray-700">{property.house_rules || 'No house rules configured yet.'}</p>
            </section>
          )}

          {/* Nearby Places Tab */}
          {activeTab === 'nearby' && (
            <section className="rounded-lg bg-white p-6 shadow">
              <h2 className="text-xl font-semibold">Nearby Places & Attractions</h2>
              <p className="mt-2 text-sm text-gray-600">Describe nearby attractions, landmarks, and travel distances.</p>
              <div className="mt-4 rounded border border-gray-200 p-3 bg-gray-50">
                <pre className="whitespace-pre-wrap text-sm font-mono text-gray-700">{property.nearby_attractions || 'No information added yet.'}</pre>
              </div>
            </section>
          )}

          {/* Approval Tab */}
          {activeTab === 'approval' && (
            <section className="rounded-lg bg-white p-6 shadow">
              <h2 className="text-xl font-semibold">Submit for Approval</h2>
              <div className="mt-4 space-y-2">
                <p className="text-sm">Before submitting, ensure:</p>
                <ul className="ml-4 space-y-1 text-sm text-gray-700">
                  <li>✓ Property details complete</li>
                  <li>{photos.length > 0 ? '✓' : '✗'} At least 1 property photo</li>
                  <li>{property.room_types?.length > 0 ? '✓' : '✗'} At least 1 room type</li>
                  <li>✓ Pricing configured</li>
                </ul>
              </div>
              <button className="mt-6 rounded-lg bg-green-600 px-6 py-2 text-white hover:bg-green-700 disabled:opacity-50" disabled={photos.length === 0 || !property.room_types?.length}>
                Submit for Approval
              </button>
            </section>
          )}
        </>
      )}
    </div>
  )
}
