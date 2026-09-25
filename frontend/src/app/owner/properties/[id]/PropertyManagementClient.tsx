'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import VillaDetailsSection from './VillaDetailsSection'

interface Photo {
  id: string
  cloudinary_url: string
  cloudinary_public_id?: string
  is_cover: boolean
  display_order: number
}

const MAX_PHOTO_SIZE_MB = 10
const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']

export default function PropertyManagementClient({ propertyId }: { propertyId: string }) {
  const [property, setProperty] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [photos, setPhotos] = useState<Photo[]>([])
  const [photoError, setPhotoError] = useState<string | null>(null)
  const [photoSuccess, setPhotoSuccess] = useState<string | null>(null)
  const [settingCoverId, setSettingCoverId] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{ done: number; total: number } | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitErrors, setSubmitErrors] = useState<string[] | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null)

  useEffect(() => {
    loadProperty()
  }, [propertyId])

  const loadProperty = async () => {
    try {
      // Owner-only endpoint: another owner's property id answers 404
      const data = await api.getOwnedProperty(propertyId)
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
    const deletingCover = photos.find(p => p.id === photoId)?.is_cover
    if (!confirm(deletingCover ? 'Delete the cover photo? The next photo will become the cover.' : 'Delete this photo?')) return
    try {
      setPhotoError(null)
      setPhotoSuccess(null)
      const state = await api.deletePropertyPhoto(propertyId, photoId)
      // The server promotes the next photo when the cover is deleted - use its list
      setPhotos(state?.photos ?? photos.filter(p => p.id !== photoId))
      setPhotoSuccess('Photo deleted successfully')
    } catch (err: any) {
      setPhotoError('Failed to delete photo')
    }
  }

  const handleSetCover = async (photoId: string) => {
    if (settingCoverId) return
    setSettingCoverId(photoId)
    setPhotoError(null)
    setPhotoSuccess(null)
    try {
      const state = await api.setPropertyCoverPhoto(propertyId, photoId)
      setPhotos(state.photos)
      setPhotoSuccess('Cover photo updated.')
    } catch (err: any) {
      setPhotoError(err.response?.data?.error || err.response?.data?.detail || 'Failed to set the cover photo.')
    } finally {
      setSettingCoverId(null)
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

    setUploading(true)
    setUploadProgress({ done: 0, total: files.length })
    let uploadedCount = 0
    try {
      for (const file of files) {
        const result = await api.uploadPhoto(
          file,
          () => api.getPropertyUploadSignature(propertyId),
          (data) => api.addPropertyPhoto(propertyId, data)
        )
        setPhotos(current => [...current, {
          id: result.id,
          cloudinary_url: result.cloudinary_url,
          cloudinary_public_id: result.cloudinary_public_id,
          is_cover: result.is_cover,
          display_order: result.display_order,
        }])
        uploadedCount += 1
        setUploadProgress({ done: uploadedCount, total: files.length })
      }
      setPhotoSuccess(`${uploadedCount} photo(s) uploaded successfully.`)
    } catch (err: any) {
      setPhotoError(
        uploadedCount > 0
          ? `Uploaded ${uploadedCount} of ${files.length} photo(s) before an error: ${err.message || 'upload failed'}`
          : (err.response?.data?.error || err.message || 'Upload failed. Please try again.')
      )
    } finally {
      setUploading(false)
      setUploadProgress(null)
    }
  }

  const handleSubmitForApproval = async () => {
    if (submitting) return
    setSubmitting(true)
    setSubmitErrors(null)
    setSubmitSuccess(null)
    try {
      // Backend is authoritative: it re-validates photos, rooms, pricing and availability.
      const updated = await api.submitPropertyForApproval(propertyId)
      setProperty(updated)
      setSubmitSuccess('Property submitted for approval. An admin will review it shortly.')
    } catch (err: any) {
      const data = err.response?.data
      setSubmitErrors(
        Array.isArray(data?.errors) && data.errors.length > 0
          ? data.errors
          : [data?.error || data?.detail || 'Unable to submit this property. Please try again.']
      )
    } finally {
      setSubmitting(false)
    }
  }

  const isVilla = property?.booking_mode === 'whole_property'

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'photos', label: 'Photos' },
    // Entry Villa is booked as a whole: villa-level details replace rooms
    { id: 'rooms', label: isVilla ? 'Villa Details' : 'Rooms' },
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
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-xl font-semibold">Property Overview</h2>
                {['draft', 'rejected'].includes(property.status) && (
                  <Link
                    href={`/owner/properties/add?propertyId=${encodeURIComponent(propertyId)}`}
                    className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                  >
                    Edit details
                  </Link>
                )}
              </div>
              <p className="mt-3 whitespace-pre-wrap text-gray-700">{property.description}</p>
              <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <div><dt className="font-semibold">Address</dt><dd>{property.address}, {property.city}</dd></div>
                <div><dt className="font-semibold">Type</dt><dd>{property.property_type?.name || 'Not set'}</dd></div>
                <div><dt className="font-semibold">Contact</dt><dd>{property.contact?.contact_phone || property.contact?.email || 'Not provided'}</dd></div>
                <div><dt className="font-semibold">WhatsApp</dt><dd>{property.contact?.whatsapp_number ? `+${property.contact.whatsapp_number}` : 'Not provided'}</dd></div>
              </dl>
            </section>
          )}

          {/* Photos Tab */}
          {activeTab === 'photos' && (
            <section className="rounded-lg bg-white p-6 shadow">
              <h2 className="text-xl font-semibold">Property Photos</h2>
              <p className="mt-2 text-sm text-gray-600">
                {photos.length} photo{photos.length === 1 ? '' : 's'} uploaded. The cover photo is shown on property cards, search results and as the main image of your listing.
              </p>

              {photoError && <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">{photoError}</div>}
              {photoSuccess && <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-3 text-green-800">{photoSuccess}</div>}

              <label className="mt-6 flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 p-8 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  multiple
                  className="hidden"
                  disabled={uploading}
                  onChange={(e) => handleUploadPhotos(e.target.files)}
                />
                {uploading ? (
                  <p className="text-sm text-gray-600">
                    Uploading {uploadProgress?.done ?? 0} of {uploadProgress?.total ?? 0}...
                  </p>
                ) : (
                  <>
                    <p className="font-medium text-gray-700">Click to upload photos</p>
                    <p className="text-xs text-gray-500">JPEG, PNG, or WebP - up to {MAX_PHOTO_SIZE_MB}MB each - select multiple at once</p>
                  </>
                )}
              </label>

              <div className="mt-6 grid gap-4 sm:grid-cols-2 md:grid-cols-3">
                {photos.map(photo => (
                  <div key={photo.id} className="relative">
                    <img
                      src={photo.cloudinary_url}
                      alt="property"
                      className={`h-40 w-full rounded-lg object-cover ${photo.is_cover ? 'ring-4 ring-blue-600' : ''}`}
                    />
                    {photo.is_cover && <span className="absolute top-2 left-2 rounded bg-blue-600 px-2 py-1 text-xs font-semibold text-white">Cover Photo</span>}
                    <div className="mt-2 flex gap-2">
                      {!photo.is_cover && (
                        <button
                          onClick={() => handleSetCover(photo.id)}
                          disabled={settingCoverId !== null}
                          className="flex-1 rounded bg-blue-50 px-3 py-2 text-sm text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                        >
                          {settingCoverId === photo.id ? 'Setting...' : 'Set as Cover'}
                        </button>
                      )}
                      <button
                        onClick={() => handleDeletePhoto(photo.id)}
                        className="flex-1 rounded bg-red-50 px-3 py-2 text-sm text-red-600 hover:bg-red-100"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              {photos.length === 0 && <p className="mt-4 text-sm text-gray-500">No photos yet - upload your first one above.</p>}
            </section>
          )}

          {/* Villa Details (Entry Villa - whole property) */}
          {activeTab === 'rooms' && isVilla && (
            <VillaDetailsSection
              propertyId={propertyId}
              editable={['draft', 'rejected'].includes(property.status)}
              onSaved={loadProperty}
            />
          )}

          {/* Rooms Tab */}
          {activeTab === 'rooms' && !isVilla && (
            <section className="rounded-lg bg-white p-6 shadow">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-semibold">Room Types</h2>
                  <p className="mt-2 text-sm text-gray-600">{property.room_types?.length || 0} room type(s) configured</p>
                </div>
                <div className="flex gap-2">
                  <Link
                    href={`/owner/properties/rooms?propertyId=${encodeURIComponent(propertyId)}`}
                    className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 font-medium"
                  >
                    Manage Rooms
                  </Link>
                  <Link
                    href={`/owner/properties/rooms/add?propertyId=${encodeURIComponent(propertyId)}`}
                    className="rounded-lg bg-green-600 px-4 py-2 text-white hover:bg-green-700 font-medium"
                  >
                    + Add Room
                  </Link>
                </div>
              </div>

              {property.room_types && property.room_types.length > 0 ? (
                <div className="space-y-3">
                  {property.room_types.map((room: any) => (
                    <div key={room.id} className="rounded-lg border border-gray-200 p-4 hover:border-blue-300 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-semibold text-lg text-gray-900">{room.name}</h3>
                          <p className="text-sm text-gray-600 mt-1">
                            {room.room_type} • {room.max_adults} adults, {room.max_children || 0} children
                          </p>
                          <p className="text-xs text-gray-500 mt-2">
                            {room.number_of_beds} bed(s) • {room.total_rooms} unit(s) • {room.room_size_sqft || '?'} sqft
                          </p>
                        </div>
                        <Link
                          href={`/owner/properties/rooms/photos?propertyId=${encodeURIComponent(propertyId)}&roomId=${room.id}`}
                          className="px-3 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded transition-colors"
                        >
                          Photos
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg bg-gray-50 p-6 text-center text-gray-600">
                  <p className="mb-3">No rooms configured yet.</p>
                  <Link
                    href={`/owner/properties/rooms/add?propertyId=${encodeURIComponent(propertyId)}`}
                    className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium"
                  >
                    Add Your First Room
                  </Link>
                </div>
              )}

              <p className="mt-6 text-xs text-gray-500 bg-blue-50 p-3 rounded">
                💡 Each room type needs its own 1–5 photos. Room photos are distinct from the property photos above.
              </p>
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
                  <li>{photos.length >= 5 ? '✓' : '✗'} At least 5 property photos ({photos.length} uploaded)</li>
                  {isVilla ? (
                    <li>{property.room_types?.length > 0 ? '✓' : '✗'} Villa details set (capacity, beds and nightly price)</li>
                  ) : (
                    <>
                      <li>{property.room_types?.length > 0 ? '✓' : '✗'} At least 1 room type</li>
                      <li>• Every room has 1–5 photos and pricing configured</li>
                    </>
                  )}
                </ul>
              </div>
              {submitErrors && (
                <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                  <p className="font-semibold">This property can&apos;t be submitted yet:</p>
                  <ul className="ml-4 mt-2 list-disc space-y-1">
                    {submitErrors.map((message) => <li key={message}>{message}</li>)}
                  </ul>
                </div>
              )}
              {submitSuccess && <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">{submitSuccess}</div>}
              {['draft', 'rejected'].includes(property.status) ? (
                <button
                  type="button"
                  onClick={handleSubmitForApproval}
                  className="mt-6 rounded-lg bg-green-600 px-6 py-2 text-white hover:bg-green-700 disabled:opacity-50"
                  disabled={submitting || photos.length < 5 || !property.room_types?.length}
                >
                  {submitting ? 'Submitting...' : 'Submit for Approval'}
                </button>
              ) : (
                !submitSuccess && (
                  <p className="mt-6 text-sm text-gray-600">
                    This property is {String(property.status).replace('_', ' ')} - it can only be submitted while in draft or after rejection.
                  </p>
                )
              )}
            </section>
          )}
        </>
      )}
    </div>
  )
}
