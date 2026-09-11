/**
 * Property details page with photos, rooms, and booking form
 */

'use client'

import { useEffect, useState, Suspense } from 'react'
import { useParams } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { useAuth } from '@/stores/auth'
import { api } from '@/lib/api'
import type { Property, BookingPrice } from '@/types'
import {
  Star,
  MapPin,
  Wifi,
  Users,
  Calendar,
  Heart,
  Share2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { useState as useFormState } from 'react'

function PropertyContent() {
  const params = useParams()
  const propertyId = params.id as string
  const { isAuthenticated } = useAuth()

  const [property, setProperty] = useState<Property | null>(null)
  const [loading, setLoading] = useState(true)
  const [photoIndex, setPhotoIndex] = useState(0)
  const [checkIn, setCheckIn] = useState('')
  const [checkOut, setCheckOut] = useState('')
  const [guests, setGuests] = useState(2)
  const [priceBreakdown, setPriceBreakdown] = useState<BookingPrice | null>(null)
  const [calculating, setCalculating] = useState(false)
  const [bookingLoading, setBookingLoading] = useState(false)

  // Load property
  useEffect(() => {
    async function loadProperty() {
      try {
        setLoading(true)
        const data = await api.getProperty(propertyId)
        setProperty(data)
      } catch (error) {
        console.error('Failed to load property:', error)
      } finally {
        setLoading(false)
      }
    }

    loadProperty()
  }, [propertyId])

  // Calculate price when dates change
  useEffect(() => {
    async function calculatePrice() {
      if (!property || !checkIn || !checkOut || !property.photos[0]) return

      try {
        setCalculating(true)
        const price = await api.calculatePrice({
          room_type_id: property.photos[0].id, // Use first room type as example
          check_in: checkIn,
          check_out: checkOut,
          num_adults: guests,
        })
        setPriceBreakdown(price)
      } catch (error) {
        console.error('Failed to calculate price:', error)
      } finally {
        setCalculating(false)
      }
    }

    const timer = setTimeout(calculatePrice, 500)
    return () => clearTimeout(timer)
  }, [checkIn, checkOut, guests, property])

  const handleBooking = async () => {
    if (!isAuthenticated) {
      window.location.href = '/login'
      return
    }

    if (!checkIn || !checkOut) {
      alert('Please select check-in and check-out dates')
      return
    }

    try {
      setBookingLoading(true)
      const booking = await api.createBooking({
        room_type_id: property?.photos[0].id || '',
        check_in: checkIn,
        check_out: checkOut,
        num_adults: guests,
        num_children: 0,
      })
      window.location.href = `/booking/${booking.id}`
    } catch (error) {
      console.error('Failed to create booking:', error)
      alert('Failed to create booking. Please try again.')
    } finally {
      setBookingLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">Loading property details...</p>
      </div>
    )
  }

  if (!property) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 mb-4">Property not found</p>
        <Link href="/search" className="btn-primary">
          Back to Search
        </Link>
      </div>
    )
  }

  const photos = property.photos.length > 0 ? property.photos : []
  const currentPhoto = photos[photoIndex] || { url: 'https://via.placeholder.com/800x600' }

  return (
    <div className="container py-8">
      {/* Back Button */}
      <Link href="/search" className="flex items-center gap-2 text-primary hover:text-secondary mb-6">
        <ChevronLeft className="w-5 h-5" />
        Back to Search
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2">
          {/* Photo Gallery */}
          <div className="mb-8">
            <div className="relative h-96 w-full bg-gray-200 rounded-lg overflow-hidden mb-4">
              <Image
                src={currentPhoto.url}
                alt={property.name}
                fill
                className="object-cover"
                sizes="(max-width: 768px) 100vw, 66vw"
              />

              {photos.length > 1 && (
                <>
                  <button
                    onClick={() => setPhotoIndex(Math.max(0, photoIndex - 1))}
                    className="absolute left-4 top-1/2 -translate-y-1/2 bg-white rounded-full p-2 hover:bg-gray-100"
                  >
                    <ChevronLeft className="w-6 h-6" />
                  </button>
                  <button
                    onClick={() => setPhotoIndex(Math.min(photos.length - 1, photoIndex + 1))}
                    className="absolute right-4 top-1/2 -translate-y-1/2 bg-white rounded-full p-2 hover:bg-gray-100"
                  >
                    <ChevronRight className="w-6 h-6" />
                  </button>
                </>
              )}
            </div>

            {/* Photo Thumbnails */}
            {photos.length > 1 && (
              <div className="flex gap-2 overflow-x-auto">
                {photos.map((photo, idx) => (
                  <button
                    key={idx}
                    onClick={() => setPhotoIndex(idx)}
                    className={`relative w-24 h-24 rounded-lg overflow-hidden flex-shrink-0 ${
                      idx === photoIndex ? 'ring-2 ring-primary' : ''
                    }`}
                  >
                    <Image
                      src={photo.url}
                      alt={`Photo ${idx + 1}`}
                      fill
                      className="object-cover"
                    />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Property Info */}
          <div className="mb-8">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-4xl font-bold mb-2">{property.name}</h1>
                <div className="flex items-center gap-4 text-gray-600">
                  <div className="flex items-center gap-1">
                    <MapPin className="w-5 h-5" />
                    <span>{property.city}, {property.district}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Star className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                    <span className="font-semibold">{property.rating.toFixed(1)}</span>
                    <span>({property.review_count} reviews)</span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <button className="p-3 border border-gray-300 rounded-lg hover:bg-gray-50">
                  <Heart className="w-6 h-6" />
                </button>
                <button className="p-3 border border-gray-300 rounded-lg hover:bg-gray-50">
                  <Share2 className="w-6 h-6" />
                </button>
              </div>
            </div>

            {/* Property Type */}
            <div className="badge mb-4">{property.property_type.name}</div>
          </div>

          {/* Amenities */}
          {property.amenities.length > 0 && (
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-4">Amenities</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {property.amenities.map((amenity) => (
                  <div key={amenity.id} className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                    <Wifi className="w-5 h-5 text-gray-600" />
                    <span className="text-gray-700">{amenity.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Description */}
          <div className="mb-8">
            <h2 className="text-2xl font-bold mb-4">About This Property</h2>
            <p className="text-gray-600 leading-relaxed">{property.description || 'No description available'}</p>
          </div>
        </div>

        {/* Booking Sidebar */}
        <div className="lg:col-span-1">
          <div className="card p-6 sticky top-20">
            {/* Price */}
            <div className="mb-6">
              <p className="text-gray-600 text-sm">Starting from</p>
              <p className="text-3xl font-bold text-primary">
                LKR {property.price_range_min.toLocaleString()}
              </p>
              <p className="text-gray-600 text-sm">per night</p>
            </div>

            {/* Booking Form */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold mb-2">Check-in</label>
                <input
                  type="date"
                  value={checkIn}
                  onChange={(e) => setCheckIn(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2">Check-out</label>
                <input
                  type="date"
                  value={checkOut}
                  onChange={(e) => setCheckOut(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2">Guests</label>
                <input
                  type="number"
                  min="1"
                  value={guests}
                  onChange={(e) => setGuests(parseInt(e.target.value) || 1)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
            </div>

            {/* Price Breakdown */}
            {priceBreakdown && (
              <div className="mt-6 pt-6 border-t border-gray-200 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Base price</span>
                  <span>LKR {priceBreakdown.base_price.toLocaleString()}</span>
                </div>
                {priceBreakdown.guest_fees > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Guest fees</span>
                    <span>LKR {priceBreakdown.guest_fees.toLocaleString()}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-600">Tax</span>
                  <span>LKR {priceBreakdown.tax.toLocaleString()}</span>
                </div>
                <div className="flex justify-between font-bold text-lg pt-2 border-t">
                  <span>Total</span>
                  <span className="text-primary">LKR {priceBreakdown.total_price.toLocaleString()}</span>
                </div>
              </div>
            )}

            {/* Book Button */}
            <button
              onClick={handleBooking}
              disabled={!checkIn || !checkOut || bookingLoading || calculating}
              className="w-full btn-primary mt-6 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {bookingLoading ? 'Booking...' : 'Book Now'}
            </button>

            {!isAuthenticated && (
              <p className="text-xs text-gray-600 mt-2 text-center">
                <Link href="/login" className="text-primary hover:underline">
                  Sign in
                </Link>
                {' '}to book this property
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function PropertyPage() {
  return (
    <Suspense fallback={<div className="text-center py-12">Loading...</div>}>
      <PropertyContent />
    </Suspense>
  )
}
