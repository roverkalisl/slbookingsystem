/**
 * Admin Property Detail & Review - Approve/reject properties
 */

// Required for static export with dynamic routes
export async function generateStaticParams() {
  return [{ id: '0' }]
}

'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Property } from '@/types'
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  MapPin,
  Users,
  DollarSign,
  Star,
  Phone,
  Mail,
  AlertCircle,
  Loader2,
} from 'lucide-react'

interface ReviewAction {
  action: 'approve' | 'reject' | null
  loading: boolean
  error: string | null
}

export default function AdminPropertyDetail() {
  const router = useRouter()
  const params = useParams()
  const propertyId = params?.id as string

  const [property, setProperty] = useState<Property | null>(null)
  const [loading, setLoading] = useState(true)
  const [rejectionReason, setRejectionReason] = useState('')
  const [reviewAction, setReviewAction] = useState<ReviewAction>({
    action: null,
    loading: false,
    error: null,
  })

  useEffect(() => {
    loadProperty()
  }, [propertyId])

  const loadProperty = async () => {
    try {
      setLoading(true)
      // Since getProperties returns paginated list, we need to fetch and filter
      const response = await api.getProperties()
      const properties = response.results || []
      const found = properties.find(p => p.id.toString() === propertyId)
      if (found) {
        setProperty(found)
      } else {
        setReviewAction(prev => ({ ...prev, error: 'Property not found' }))
      }
    } catch (error) {
      console.error('Failed to load property:', error)
      setReviewAction(prev => ({ ...prev, error: 'Failed to load property' }))
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async () => {
    if (!property) return

    try {
      setReviewAction({ action: 'approve', loading: true, error: null })
      await api.approveProperty(property.id)
      // Redirect back to properties list after successful approval
      router.push('/admin/properties?status=approved')
    } catch (error: any) {
      setReviewAction({
        action: 'approve',
        loading: false,
        error: error.message || 'Failed to approve property',
      })
    }
  }

  const handleReject = async () => {
    if (!property || !rejectionReason.trim()) {
      setReviewAction(prev => ({
        ...prev,
        error: 'Please provide a rejection reason',
      }))
      return
    }

    try {
      setReviewAction({ action: 'reject', loading: true, error: null })
      await api.rejectProperty(property.id, rejectionReason)
      // Redirect back to properties list
      router.push('/admin/properties?status=rejected')
    } catch (error: any) {
      setReviewAction({
        action: 'reject',
        loading: false,
        error: error.message || 'Failed to reject property',
      })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-600">Loading property details...</p>
      </div>
    )
  }

  if (!property) {
    return (
      <div>
        <Link
          href="/admin/properties"
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Properties
        </Link>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-800">Property not found</p>
        </div>
      </div>
    )
  }

  const isPending = property.status === 'pending_approval'
  const isApproved = property.status === 'approved'

  return (
    <div>
      {/* Back Button */}
      <Link
        href="/admin/properties"
        className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Properties
      </Link>

      {/* Property Header */}
      <div className="bg-white rounded-lg shadow mb-6 p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{property.name}</h1>
            <p className="text-gray-600 mt-2">{property.short_description}</p>
          </div>
          <div className="text-right">
            <div className={`inline-block px-4 py-2 rounded-full font-semibold text-sm ${
              property.status === 'pending_approval'
                ? 'bg-yellow-100 text-yellow-800'
                : property.status === 'approved'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
            }`}>
              {(property.status || 'unknown').replace('_', ' ').toUpperCase()}
            </div>
          </div>
        </div>

        {/* Key Info Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-600">Property Type</p>
            <p className="font-semibold text-gray-900 mt-1">{property.property_type}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Bedrooms</p>
            <p className="font-semibold text-gray-900 mt-1">{property.bedrooms}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Bathrooms</p>
            <p className="font-semibold text-gray-900 mt-1">{property.bathrooms}</p>
          </div>
          <div>
            <p className="text-sm text-gray-600">Max Guests</p>
            <p className="font-semibold text-gray-900 mt-1">{property.max_guests}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Location */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
              <MapPin className="w-5 h-5 text-red-600" />
              Location
            </h2>
            <div className="space-y-3">
              <div>
                <p className="text-sm text-gray-600">Address</p>
                <p className="font-medium text-gray-900">{property.address}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">City</p>
                  <p className="font-medium text-gray-900">{property.city}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">District</p>
                  <p className="font-medium text-gray-900">{property.district}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Province</p>
                  <p className="font-medium text-gray-900">{property.province || '—'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Postal Code</p>
                  <p className="font-medium text-gray-900">{property.postal_code || '—'}</p>
                </div>
              </div>
              {property.google_maps_url && (
                <a
                  href={property.google_maps_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                >
                  View on Google Maps →
                </a>
              )}
            </div>
          </div>

          {/* Description */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4">Description</h2>
            <p className="text-gray-700 whitespace-pre-line">{property.description}</p>
          </div>

          {/* House Rules & Nearby Attractions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {property.house_rules && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-bold mb-3">House Rules</h2>
                <p className="text-gray-700 text-sm whitespace-pre-line">{property.house_rules}</p>
              </div>
            )}
            {property.nearby_attractions && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-bold mb-3">Nearby Attractions</h2>
                <p className="text-gray-700 text-sm whitespace-pre-line">{property.nearby_attractions}</p>
              </div>
            )}
          </div>

          {/* Amenities */}
          {property.amenities && property.amenities.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold mb-4">Amenities</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {property.amenities.map((amenity, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-3 bg-gray-50 rounded">
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                    <span className="text-sm text-gray-900">{amenity.name || amenity}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Submission Info */}
          {isPending && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
                <Clock className="w-5 h-5 text-blue-600" />
                Submission Information
              </h2>
              <div className="space-y-2">
                <p className="text-sm">
                  <span className="text-gray-600">Submitted:</span>{' '}
                  <span className="font-medium">
                    {property.submitted_at
                      ? new Date(property.submitted_at).toLocaleString()
                      : '—'}
                  </span>
                </p>
              </div>
            </div>
          )}

          {/* Rejection Info (if rejected before) */}
          {property.rejection_reason && property.status === 'rejected' && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-600" />
                Previous Rejection
              </h2>
              <p className="text-sm text-red-800">{property.rejection_reason}</p>
            </div>
          )}
        </div>

        {/* Sidebar: Owner Info & Actions */}
        <div className="space-y-6">
          {/* Owner Contact Info */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-gray-600" />
              Owner Information
            </h2>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-gray-600">Name</p>
                <p className="font-medium text-gray-900">
                  {property.owner?.first_name} {property.owner?.last_name}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Email</p>
                <a
                  href={`mailto:${property.owner?.email}`}
                  className="font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
                >
                  <Mail className="w-4 h-4" />
                  {property.owner?.email}
                </a>
              </div>

              {/* Property Contact Info if available */}
              {property.contact && (
                <>
                  <hr className="my-3" />
                  <div>
                    <p className="text-sm text-gray-600">Contact Person</p>
                    <p className="font-medium text-gray-900">
                      {property.contact.contact_person_name}
                    </p>
                  </div>
                  {property.contact.contact_phone && (
                    <div>
                      <p className="text-sm text-gray-600">Phone</p>
                      <a
                        href={`tel:${property.contact.contact_phone}`}
                        className="font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
                      >
                        <Phone className="w-4 h-4" />
                        {property.contact.contact_phone}
                      </a>
                    </div>
                  )}
                  {property.contact.whatsapp_number && (
                    <div>
                      <p className="text-sm text-gray-600">WhatsApp</p>
                      <a
                        href={`https://wa.me/${property.contact.whatsapp_number}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-green-600 hover:text-green-700 flex items-center gap-1"
                      >
                        WhatsApp: {property.contact.whatsapp_number}
                      </a>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Stats */}
          {isApproved && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-bold mb-4">Performance</h2>
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-gray-600">Average Rating</p>
                  <p className="text-2xl font-bold text-orange-500 flex items-center gap-1">
                    {property.average_rating?.toFixed(1) || 'N/A'}
                    <Star className="w-5 h-5 fill-current" />
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Total Reviews</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {property.total_reviews || 0}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Action Panel */}
          {isPending && (
            <div className="bg-white rounded-lg shadow p-6 border-2 border-blue-200">
              <h2 className="text-lg font-bold mb-4">Review Actions</h2>

              {reviewAction.error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-800">
                  {reviewAction.error}
                </div>
              )}

              <div className="space-y-3">
                {/* Approve Button */}
                <button
                  onClick={handleApprove}
                  disabled={reviewAction.loading}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
                >
                  {reviewAction.loading && reviewAction.action === 'approve' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Approving...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      Approve Property
                    </>
                  )}
                </button>

                {/* Reject Reason Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-900 mb-2">
                    Rejection Reason (if rejecting)
                  </label>
                  <textarea
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="Explain why this property doesn't meet our standards..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
                    rows={4}
                  />
                </div>

                {/* Reject Button */}
                <button
                  onClick={handleReject}
                  disabled={reviewAction.loading || !rejectionReason.trim()}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
                >
                  {reviewAction.loading && reviewAction.action === 'reject' ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Rejecting...
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4" />
                      Reject Property
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {isApproved && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-6">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-1" />
                <div>
                  <p className="font-semibold text-green-900">Property Approved</p>
                  <p className="text-sm text-green-700 mt-1">
                    This property is live and visible to guests
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
