/**
 * Property details - Client Component
 * Handles all interactive UI: photos, booking form, price calculation
 */

'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { useAuth } from '@/stores/auth'
import { api } from '@/lib/api'
import { useDynamicRouteId } from '@/lib/useDynamicRouteId'
import type { Property, BookingPrice } from '@/types'
import {
  Star,
  MapPin,
  Wifi,
  Heart,
  Share2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'

export function PropertyContent() {
  const params = useParams()
  // Real id from the URL - useParams() returns the static-export placeholder '0'
  const propertyId = useDynamicRouteId(params.id as string)
  const { isAuthenticated } = useAuth()

  const [property, setProperty] = useState<Property | null>(null)
  const [loading, setLoading] = useState(true)
  const [photoIndex, setPhotoIndex] = useState(0)
  const [selectedRoomTypeId, setSelectedRoomTypeId] = useState<string>('')
  const [checkIn, setCheckIn] = useState('')
  const [checkOut, setCheckOut] = useState('')
  const [guests, setGuests] = useState(2)
  const [priceBreakdown, setPriceBreakdown] = useState<BookingPrice | null>(null)
  const [calculating, setCalculating] = useState(false)
  const [bookingLoading, setBookingLoading] = useState(false)
  const [availability, setAvailability] = useState<{ available: boolean; available_count: number } | null>(null)
  const [checkingAvailability, setCheckingAvailability] = useState(false)
  const [bookingError, setBookingError] = useState<string | null>(null)

  const selectedRoom = property?.room_types?.find(rt => rt.id === selectedRoomTypeId) || null
  // Entry Villa (whole property): booked as one unit, shown as "Entire Villa"
  const isVilla = property?.booking_mode === 'whole_property'
  const villaUnit = isVilla ? property?.room_types?.find(rt => rt.is_property_unit) || null : null

  // Load property
  useEffect(() => {
    if (!propertyId) return
    async function loadProperty() {
      try {
        setLoading(true)
        const data = await api.getProperty(propertyId as string)
        setProperty(data)
        // Auto-select only when there's exactly one room type - otherwise
        // the guest must explicitly choose (never silently default to [0]
        // when there's more than one option). An Entry Villa always uses its
        // single "Entire Villa" unit - there is no room-selection step.
        const unit = data.booking_mode === 'whole_property'
          ? data.room_types?.find((r) => r.is_property_unit)
          : data.room_types?.length === 1 ? data.room_types[0] : undefined
        if (unit) {
          setSelectedRoomTypeId(unit.id)
        }
      } catch (error) {
        console.error('Failed to load property:', error)
      } finally {
        setLoading(false)
      }
    }

    loadProperty()
  }, [propertyId])

  // Calculate price when the selected room or dates change
  useEffect(() => {
    async function calculatePrice() {
      if (!selectedRoomTypeId || !checkIn || !checkOut) {
        setPriceBreakdown(null)
        return
      }

      try {
        setCalculating(true)
        const price = await api.calculatePrice({
          room_type_id: selectedRoomTypeId,
          check_in: checkIn,
          check_out: checkOut,
          num_adults: guests,
        })
        setPriceBreakdown(price)
      } catch (error) {
        console.error('Failed to calculate price:', error)
        setPriceBreakdown(null)
      } finally {
        setCalculating(false)
      }
    }

    const timer = setTimeout(calculatePrice, 500)
    return () => clearTimeout(timer)
  }, [checkIn, checkOut, guests, selectedRoomTypeId])

  // Availability pre-check (UX only - the backend re-validates authoritatively
  // inside booking creation, so this never replaces that check).
  useEffect(() => {
    async function runAvailabilityCheck() {
      if (!selectedRoomTypeId || !checkIn || !checkOut) {
        setAvailability(null)
        return
      }

      try {
        setCheckingAvailability(true)
        const result = await api.checkAvailability(selectedRoomTypeId, checkIn, checkOut)
        setAvailability(result)
      } catch (error) {
        console.error('Failed to check availability:', error)
        setAvailability(null)
      } finally {
        setCheckingAvailability(false)
      }
    }

    const timer = setTimeout(runAvailabilityCheck, 500)
    return () => clearTimeout(timer)
  }, [checkIn, checkOut, selectedRoomTypeId])

  const handleBooking = async () => {
    if (!isAuthenticated) {
      window.location.href = '/login'
      return
    }

    setBookingError(null)

    if (!selectedRoomTypeId) {
      setBookingError('Please select a room type first.')
      return
    }

    if (!checkIn || !checkOut) {
      setBookingError('Please select check-in and check-out dates.')
      return
    }

    try {
      setBookingLoading(true)
      const booking = await api.createBooking({
        room_type_id: selectedRoomTypeId,
        check_in: checkIn,
        check_out: checkOut,
        num_adults: guests,
        num_children: 0,
      })
      // /booking/{id} has no page in this static export - send the guest to
      // My Bookings, where the booking (and its payment action) is listed.
      window.location.href = '/bookings'
    } catch (error: any) {
      console.error('Failed to create booking:', error)
      // Backend is the final authority on availability (HTTP 409) even if
      // the client-side pre-check above said it looked available.
      if (error.response?.status === 409) {
        setBookingError(error.response.data?.detail || error.response.data?.error || 'The selected room is no longer available for these dates.')
      } else if (error.response?.data) {
        const data = error.response.data
        setBookingError(typeof data === 'string' ? data : (data.detail || data.error || 'Failed to create booking. Please try again.'))
      } else {
        setBookingError('Failed to create booking. Please try again.')
      }
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

          {/* Entry Villa - the whole villa is the bookable unit: no room selection */}
          {isVilla && villaUnit && (
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-4">Entire Villa</h2>
              <div className="rounded-lg border-2 border-primary bg-blue-50 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-gray-700">You book the whole villa - it&apos;s all yours.</p>
                    <div className="flex flex-wrap gap-3 mt-2 text-sm text-gray-600">
                      <span>{villaUnit.max_adults} adult{villaUnit.max_adults === 1 ? '' : 's'}</span>
                      {villaUnit.max_children > 0 && <span>{villaUnit.max_children} child{villaUnit.max_children === 1 ? '' : 'ren'}</span>}
                      <span>up to {villaUnit.total_occupancy} guest{villaUnit.total_occupancy === 1 ? '' : 's'}</span>
                      {villaUnit.number_of_beds && (
                        <span>{villaUnit.number_of_beds} bed{villaUnit.number_of_beds === 1 ? '' : 's'}{villaUnit.bed_configuration ? ` (${villaUnit.bed_configuration})` : ''}</span>
                      )}
                      {villaUnit.bathroom_type && <span>{villaUnit.bathroom_type.replace('_', ' ')} bathroom</span>}
                    </div>
                  </div>
                  {villaUnit.pricing?.base_price != null && (
                    <div className="text-right flex-shrink-0">
                      <p className="text-lg font-bold text-primary">LKR {Number(villaUnit.pricing.base_price).toLocaleString()}</p>
                      <p className="text-xs text-gray-500">per night</p>
                      {villaUnit.pricing.weekend_price && (
                        <p className="text-xs text-gray-500">Weekends LKR {Number(villaUnit.pricing.weekend_price).toLocaleString()}</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Room Types - guest must explicitly choose when there's more than one */}
          {!isVilla && property.room_types && property.room_types.length > 0 && (
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-4">Available Rooms</h2>
              <div className="space-y-4">
                {property.room_types.map((room) => {
                  const isSelected = room.id === selectedRoomTypeId
                  const roomPhoto = room.photos?.[0]
                  const nightlyPrice = room.pricing?.base_price
                  return (
                    <div
                      key={room.id}
                      className={`rounded-lg border-2 p-4 transition-colors ${isSelected ? 'border-primary bg-blue-50' : 'border-gray-200'}`}
                    >
                      <div className="flex flex-col sm:flex-row gap-4">
                        {roomPhoto && (
                          <div className="relative h-32 w-full sm:w-48 flex-shrink-0 rounded-lg overflow-hidden bg-gray-100">
                            <Image src={roomPhoto.cloudinary_url || (roomPhoto as any).url} alt={room.name} fill className="object-cover" />
                          </div>
                        )}
                        <div className="flex-1">
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <h3 className="text-lg font-bold">{room.name}</h3>
                              {room.description && <p className="text-sm text-gray-600 mt-1">{room.description}</p>}
                            </div>
                            {nightlyPrice != null && (
                              <div className="text-right flex-shrink-0">
                                <p className="text-lg font-bold text-primary">LKR {Number(nightlyPrice).toLocaleString()}</p>
                                <p className="text-xs text-gray-500">per night</p>
                              </div>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-3 mt-2 text-sm text-gray-600">
                            <span>{room.max_adults} adult{room.max_adults === 1 ? '' : 's'}</span>
                            {room.max_children > 0 && <span>{room.max_children} child{room.max_children === 1 ? '' : 'ren'}</span>}
                            {(room as any).number_of_beds && <span>{(room as any).number_of_beds} bed(s)</span>}
                            {(room as any).total_rooms && <span>{(room as any).total_rooms} unit(s) available</span>}
                          </div>
                          {room.amenities && room.amenities.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-2">
                              {room.amenities.map((a: any) => (
                                <span key={a.id} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">{a.amenity_name || a.name}</span>
                              ))}
                            </div>
                          )}
                          <button
                            onClick={() => setSelectedRoomTypeId(room.id)}
                            className={`mt-3 px-4 py-2 rounded-lg text-sm font-semibold ${isSelected ? 'bg-primary text-white' : 'bg-gray-100 text-gray-800 hover:bg-gray-200'}`}
                          >
                            {isSelected ? 'Selected' : 'Select This Room'}
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

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

          {/* House Rules */}
          {property.house_rules && (
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-4">House Rules</h2>
              <p className="text-gray-600 leading-relaxed whitespace-pre-wrap">{property.house_rules}</p>
            </div>
          )}

          {/* Nearby Attractions */}
          {property.nearby_attractions && (
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-4">Nearby Attractions</h2>
              <p className="text-gray-600 leading-relaxed whitespace-pre-wrap">{property.nearby_attractions}</p>
            </div>
          )}

          {/* Contact Property */}
          {(property.contact?.whatsapp_number || property.contact?.email) && (
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-4">Contact This Property</h2>
              <div className="flex flex-wrap gap-3">
                {property.contact?.whatsapp_number && (
                  <a
                    href={`https://wa.me/${property.contact.whatsapp_number.replace(/[^\d]/g, '')}?text=${encodeURIComponent(`Hi, I have a question about ${property.name}.`)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-5 py-3 bg-green-50 text-green-700 rounded-lg font-medium hover:bg-green-100"
                  >
                    WhatsApp
                  </a>
                )}
                {property.contact?.email && (
                  <a
                    href={`mailto:${property.contact.email}?subject=${encodeURIComponent(`Question about ${property.name}`)}`}
                    className="px-5 py-3 bg-blue-50 text-blue-700 rounded-lg font-medium hover:bg-blue-100"
                  >
                    Email
                  </a>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Booking Sidebar */}
        <div className="lg:col-span-1">
          <div className="card p-6 sticky top-20">
            {/* Price */}
            <div className="mb-6">
              <p className="text-gray-600 text-sm">{selectedRoom ? selectedRoom.name : 'Starting from'}</p>
              <p className="text-3xl font-bold text-primary">
                LKR {Number(selectedRoom?.pricing?.base_price ?? property.price_range_min ?? 0).toLocaleString()}
              </p>
              <p className="text-gray-600 text-sm">per night</p>
            </div>

            {!selectedRoomTypeId && (
              <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
                {isVilla ? 'This villa is not available for booking yet.' : 'Select a room above to continue booking.'}
              </div>
            )}

            {/* Booking Form */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold mb-2">Check-in</label>
                <input
                  type="date"
                  value={checkIn}
                  min={new Date().toISOString().split('T')[0]}
                  onChange={(e) => setCheckIn(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold mb-2">Check-out</label>
                <input
                  type="date"
                  value={checkOut}
                  min={checkIn || new Date().toISOString().split('T')[0]}
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

            {/* Availability */}
            {checkingAvailability && (
              <p className="mt-4 text-sm text-gray-500">Checking availability...</p>
            )}
            {!checkingAvailability && availability && (
              availability.available ? (
                <p className="mt-4 text-sm text-green-700 bg-green-50 rounded-lg p-3">
                  Available ({availability.available_count} room{availability.available_count === 1 ? '' : 's'} left for these dates)
                </p>
              ) : (
                <p className="mt-4 text-sm text-red-700 bg-red-50 rounded-lg p-3">
                  Not available for these dates. Please choose different dates.
                </p>
              )
            )}

            {/* Price Breakdown */}
            {priceBreakdown && (
              <div className="mt-6 pt-6 border-t border-gray-200 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Room ({priceBreakdown.nights} night{priceBreakdown.nights === 1 ? '' : 's'})</span>
                  <span>LKR {Number(priceBreakdown.room_subtotal).toLocaleString()}</span>
                </div>
                {Number(priceBreakdown.guest_fees) > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Guest fees</span>
                    <span>LKR {Number(priceBreakdown.guest_fees).toLocaleString()}</span>
                  </div>
                )}
                {Number(priceBreakdown.discount) > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Discount</span>
                    <span>-LKR {Number(priceBreakdown.discount).toLocaleString()}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-600">Service fee</span>
                  <span>LKR {Number(priceBreakdown.service_fee).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Tax</span>
                  <span>LKR {Number(priceBreakdown.tax).toLocaleString()}</span>
                </div>
                <div className="flex justify-between font-bold text-lg pt-2 border-t">
                  <span>Total</span>
                  <span className="text-primary">LKR {Number(priceBreakdown.total).toLocaleString()}</span>
                </div>
              </div>
            )}

            {bookingError && (
              <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{bookingError}</div>
            )}

            {/* Book Button */}
            <button
              onClick={handleBooking}
              disabled={!selectedRoomTypeId || !checkIn || !checkOut || bookingLoading || calculating || (availability !== null && !availability.available)}
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
