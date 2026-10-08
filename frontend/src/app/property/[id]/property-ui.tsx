/**
 * Property details - Client Component
 * Handles all interactive UI: photos, booking form, price calculation
 */

'use client'

import { useEffect, useRef, useState } from 'react'
import { useParams } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import { useAuth } from '@/stores/auth'
import { api } from '@/lib/api'
import { useDynamicRouteId } from '@/lib/useDynamicRouteId'
import { normalizeWhatsAppNumber, whatsappLink } from '@/lib/whatsapp'
import { nightsBetween, trackEvent } from '@/lib/analytics'
import { bookingLoginRedirect, bookingReturnPath, loginUrl, parseBookingDraft } from '@/lib/authRedirect'
import type { Property, BookingPrice, Review } from '@/types'
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
  const { isAuthenticated, user } = useAuth()

  const [property, setProperty] = useState<Property | null>(null)
  const [loading, setLoading] = useState(true)
  const [propertyRetry, setPropertyRetry] = useState(0)
  const [propertyError, setPropertyError] = useState(false)
  const [reviews, setReviews] = useState<Review[]>([])
  const [reviewsLoading, setReviewsLoading] = useState(false)
  const [reviewsError, setReviewsError] = useState(false)
  const [photoIndex, setPhotoIndex] = useState(0)
  const [failedPhotoUrls, setFailedPhotoUrls] = useState<string[]>([])
  const [selectedRoomTypeId, setSelectedRoomTypeId] = useState<string>('')
  const [checkIn, setCheckIn] = useState('')
  const [checkOut, setCheckOut] = useState('')
  const [guests, setGuests] = useState(2)
  const [priceBreakdown, setPriceBreakdown] = useState<BookingPrice | null>(null)
  const [priceQuoteKey, setPriceQuoteKey] = useState<string | null>(null)
  const [priceError, setPriceError] = useState(false)
  const [priceRetry, setPriceRetry] = useState(0)
  const [calculating, setCalculating] = useState(false)
  const [bookingLoading, setBookingLoading] = useState(false)
  const [availability, setAvailability] = useState<{ available: boolean; available_count: number } | null>(null)
  const [availabilityError, setAvailabilityError] = useState(false)
  const [availabilityRetry, setAvailabilityRetry] = useState(0)
  const [checkingAvailability, setCheckingAvailability] = useState(false)
  const [bookingError, setBookingError] = useState<string | null>(null)
  const [showBookingReview, setShowBookingReview] = useState(false)
  // Guest WhatsApp / mobile for this booking (shared only with the property owner)
  const [guestPhone, setGuestPhone] = useState('')
  const [guestPhoneTouched, setGuestPhoneTouched] = useState(false)
  // Count/track a property view once per loaded property (not on re-renders)
  const trackedViewFor = useRef<string | null>(null)

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
        setProperty(null)
        setPropertyError(false)
        setPhotoIndex(0)
        setSelectedRoomTypeId('')
        setCheckIn('')
        setCheckOut('')
        setGuests(2)
        setPriceBreakdown(null)
        setPriceQuoteKey(null)
        setShowBookingReview(false)
        setReviews([])
        const data = await api.getProperty(propertyId as string)
        setProperty(data)
        if (data.status === 'approved' && trackedViewFor.current !== data.id) {
          trackedViewFor.current = data.id
          // Same title the server puts in the HTML for this listing (config/seo.py)
          document.title = `${data.name}${data.city ? ` - ${data.city}` : ''} | SL Booking`
          trackEvent('property_view', { property_id: data.id, property_type: data.property_type?.name, city: data.city })
          // Server-side view counter: one per visitor per day; owner/admin views are ignored by the backend
          api.recordPropertyView(data.id)
        }
        // Auto-select only when there's exactly one room type - otherwise
        // the guest must explicitly choose (never silently default to [0]
        // when there's more than one option). An Entry Villa always uses its
        // single "Entire Villa" unit - there is no room-selection step.
        const unit = data.booking_mode === 'whole_property'
          ? data.room_types?.find((r) => r.is_property_unit)
          : data.room_types?.length === 1 ? data.room_types[0] : undefined
        // Booking form saved in the URL when a signed-out guest was sent to
        // login from Book Now - restore it so they continue the same booking.
        const draft = parseBookingDraft(window.location.search)
        const draftRoom = draft.roomTypeId ? data.room_types?.find((r) => r.id === draft.roomTypeId) : undefined
        if (unit) {
          setSelectedRoomTypeId(unit.id)
        } else if (draftRoom) {
          setSelectedRoomTypeId(draftRoom.id)
        }
        if (draft.checkIn) setCheckIn(draft.checkIn)
        if (draft.checkOut) setCheckOut(draft.checkOut)
        if (draft.guests) setGuests(draft.guests)
      } catch (error) {
        console.error('Failed to load property:', error)
        setPropertyError(true)
      } finally {
        setLoading(false)
      }
    }

    loadProperty()
  }, [propertyId, propertyRetry])

  useEffect(() => {
    if (!property) return
    let cancelled = false
    setReviewsLoading(true)
    setReviewsError(false)
    api.getReviews(property.id)
      .then((data) => { if (!cancelled) setReviews(data) })
      .catch((error) => {
        console.error('Failed to load property reviews:', error)
        if (!cancelled) setReviewsError(true)
      })
      .finally(() => { if (!cancelled) setReviewsLoading(false) })
    return () => { cancelled = true }
  }, [property])

  // Calculate price when the selected room or dates change
  useEffect(() => {
    const requestKey = `${selectedRoomTypeId}|${checkIn}|${checkOut}|${guests}`
    let cancelled = false
    setPriceBreakdown(null)
    setPriceQuoteKey(null)
    setPriceError(false)
    if (!selectedRoomTypeId || !checkIn || !checkOut) {
      setCalculating(false)
      return
    }

    async function calculatePrice() {
      try {
        setCalculating(true)
        const price = await api.calculatePrice({
          room_type_id: selectedRoomTypeId,
          check_in: checkIn,
          check_out: checkOut,
          num_adults: guests,
        })
        if (!cancelled) {
          setPriceBreakdown(price)
          setPriceQuoteKey(requestKey)
        }
      } catch (error) {
        console.error('Failed to calculate price:', error)
        if (!cancelled) setPriceError(true)
      } finally {
        if (!cancelled) setCalculating(false)
      }
    }

    const timer = setTimeout(calculatePrice, 500)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [checkIn, checkOut, guests, selectedRoomTypeId, priceRetry])

  // Availability pre-check (UX only - the backend re-validates authoritatively
  // inside booking creation, so this never replaces that check).
  useEffect(() => {
    let cancelled = false
    setAvailability(null)
    setAvailabilityError(false)
    if (!selectedRoomTypeId || !checkIn || !checkOut) {
      setCheckingAvailability(false)
      return
    }

    async function runAvailabilityCheck() {
      try {
        setCheckingAvailability(true)
        const result = await api.checkAvailability(selectedRoomTypeId, checkIn, checkOut)
        if (!cancelled) setAvailability(result)
      } catch (error) {
        console.error('Failed to check availability:', error)
        if (!cancelled) setAvailabilityError(true)
      } finally {
        if (!cancelled) setCheckingAvailability(false)
      }
    }

    const timer = setTimeout(runAvailabilityCheck, 500)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [checkIn, checkOut, selectedRoomTypeId, availabilityRetry])

  // Prefill the booking contact number from the guest's profile once, if it has one
  useEffect(() => {
    if (!guestPhoneTouched && !guestPhone && user?.phone) setGuestPhone(user.phone)
  }, [user?.phone, guestPhone, guestPhoneTouched])

  const guestPhoneValid = normalizeWhatsAppNumber(guestPhone) !== null
  const quoteIsCurrent = priceQuoteKey === `${selectedRoomTypeId}|${checkIn}|${checkOut}|${guests}`

  // This property with the current booking form, to come back to after login
  // (no phone number - it is prefilled from the guest's profile instead).
  const returnPath = property
    ? bookingReturnPath(`/property/${encodeURIComponent(property.id)}`, {
        roomTypeId: selectedRoomTypeId, checkIn, checkOut, guests,
      })
    : null

  const handleBooking = () => {
    const loginRedirect = bookingLoginRedirect(isAuthenticated, returnPath ?? '')
    if (loginRedirect) {
      window.location.href = loginRedirect
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

    if (checkOut <= checkIn) {
      setBookingError('Check-out must be after check-in.')
      return
    }

    if (!guestPhoneValid) {
      setGuestPhoneTouched(true)
      setBookingError('Please enter a valid WhatsApp / mobile number, e.g. 0771234567 or +94771234567.')
      return
    }

    if (!quoteIsCurrent || !priceBreakdown) {
      setBookingError('Please wait for the latest price to load before reviewing your booking.')
      return
    }

    setBookingError(null)
    trackEvent('booking_start', { property_id: property?.id, nights: nightsBetween(checkIn, checkOut) })
    setShowBookingReview(true)
  }

  const handleConfirmBooking = async () => {
    if (!quoteIsCurrent || !priceBreakdown) {
      setShowBookingReview(false)
      setBookingError('The quote changed. Please review the current price and availability again.')
      setPriceRetry((retry) => retry + 1)
      return
    }

    const analyticsParams = { property_id: property?.id, nights: nightsBetween(checkIn, checkOut) }

    try {
      setBookingLoading(true)
      const booking = await api.createBooking({
        room_type_id: selectedRoomTypeId,
        check_in: checkIn,
        check_out: checkOut,
        num_adults: guests,
        num_children: 0,
        guest_phone: guestPhone.trim(),
        expected_total: Number(priceBreakdown.total),
      })
      // Booking created (HTTP 201) - no reference, price or guest data is sent
      trackEvent('booking_created', analyticsParams)
      // /booking/{id} has no page in this static export - send the guest to
      // My Bookings, which confirms the new booking (payment + WhatsApp owner).
      window.location.href = booking?.booking_reference
        ? `/bookings?booking_created=${encodeURIComponent(booking.booking_reference)}`
        : '/bookings'
    } catch (error: any) {
      console.error('Failed to create booking:', error)
      // Backend is the final authority on availability (HTTP 409) even if
      // the client-side pre-check above said it looked available.
      if (error.response?.status === 409) {
        const message = error.response.data?.detail || error.response.data?.error
        setBookingError(error.response.data?.error_code === 'PRICE_CHANGED'
          ? (message || 'The price changed. Please review the latest price before confirming again.')
          : (message || 'Availability changed. Please check the latest availability before confirming again.'))
        setShowBookingReview(false)
        setPriceRetry((retry) => retry + 1)
        setAvailabilityRetry((retry) => retry + 1)
      } else if (error.response?.data) {
        const data = error.response.data
        const phoneError = Array.isArray(data?.guest_phone) ? data.guest_phone[0] : data?.guest_phone
        setBookingError(typeof data === 'string' ? data : (phoneError || data.detail || data.error || 'Failed to create booking. Please try again.'))
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
        {propertyError ? (
          <>
            <p className="text-gray-700 mb-4">Unable to load this property. Please try again.</p>
            <button type="button" onClick={() => setPropertyRetry((retry) => retry + 1)} className="btn-secondary mr-3">
              Try again
            </button>
            <Link href="/search" className="btn-primary">Back to Search</Link>
          </>
        ) : (
          <>
            <p className="text-gray-600 mb-4">Property not found</p>
            <Link href="/search" className="btn-primary">Back to Search</Link>
          </>
        )}
      </div>
    )
  }

  // Cover photo first so it is the hero image; the rest follow in display order.
  const photos = [...property.photos].sort((a, b) => Number(!!b.is_cover) - Number(!!a.is_cover))
  // No external placeholder service (it no longer serves images): a property
  // without photos shows a neutral box instead of a broken image.
  const currentPhoto = photos[photoIndex] || null
  const currentPhotoAvailable = currentPhoto && !failedPhotoUrls.includes(currentPhoto.url)
  const sidebarPrice = Number(selectedRoom?.pricing?.base_price ?? property.price_range_min ?? 0)
  const propertyWhatsApp = whatsappLink(property.contact?.whatsapp_number, `Hi, I have a question about ${property.name}.`)
  const locationQuery = property.latitude != null && property.longitude != null
    ? `${property.latitude},${property.longitude}`
    : [property.address, property.city, property.district].filter(Boolean).join(', ')
  const guestName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'Name not available'

  return (
    <div className="container py-8">
      {/* Back Button */}
      <Link href="/search" className="flex items-center gap-2 text-primary hover:text-secondary mb-6">
        <ChevronLeft className="w-5 h-5" />
        Back to Search
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 lg:gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2">
          {/* Photo Gallery */}
          <div className="mb-8">
            <div className="relative h-64 sm:h-96 w-full bg-gray-100 rounded-xl overflow-hidden mb-4">
              {currentPhotoAvailable ? (
                <Image
                  src={currentPhoto.url}
                  alt={currentPhoto.caption || property.name}
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 100vw, 66vw"
                  priority
                  onError={() => setFailedPhotoUrls((urls) => [...urls, currentPhoto.url])}
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-gray-500">
                  {currentPhoto ? 'This photo is unavailable' : 'No photos available yet'}
                </div>
              )}

              {photos.length > 1 && (
                <>
                  <button
                    type="button"
                    onClick={() => setPhotoIndex(Math.max(0, photoIndex - 1))}
                    aria-label="Previous property photo"
                    disabled={photoIndex === 0}
                    className="absolute left-3 top-1/2 -translate-y-1/2 bg-white/95 rounded-full p-3 hover:bg-white disabled:opacity-50"
                  >
                    <ChevronLeft className="w-6 h-6" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setPhotoIndex(Math.min(photos.length - 1, photoIndex + 1))}
                    aria-label="Next property photo"
                    disabled={photoIndex === photos.length - 1}
                    className="absolute right-3 top-1/2 -translate-y-1/2 bg-white/95 rounded-full p-3 hover:bg-white disabled:opacity-50"
                  >
                    <ChevronRight className="w-6 h-6" />
                  </button>
                </>
              )}
            </div>

            {/* Photo Thumbnails */}
            {photos.length > 1 && (
              <div className="flex snap-x gap-2 overflow-x-auto pb-2" aria-label="Property photos">
                {photos.map((photo, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => setPhotoIndex(idx)}
                    aria-label={`Show photo ${idx + 1} of ${photos.length}`}
                    aria-current={idx === photoIndex}
                    className={`relative w-24 h-24 rounded-lg overflow-hidden flex-shrink-0 ${
                      idx === photoIndex ? 'ring-2 ring-primary' : ''
                    }`}
                  >
                    {failedPhotoUrls.includes(photo.url) ? (
                      <span className="flex h-full items-center justify-center bg-gray-100 px-2 text-center text-xs text-gray-500">Image unavailable</span>
                    ) : (
                      <Image
                        src={photo.url}
                        alt={photo.caption || `${property.name} - photo ${idx + 1} of ${photos.length}`}
                        fill
                        className="object-cover"
                        sizes="96px"
                        onError={() => setFailedPhotoUrls((urls) => [...urls, photo.url])}
                      />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Property Info */}
          <div className="mb-8">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-3xl sm:text-4xl font-bold mb-2">{property.name}</h1>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-gray-600">
                  <div className="flex items-center gap-1">
                    <MapPin className="w-5 h-5" />
                    <span>{property.city}, {property.district}</span>
                  </div>
                  {property.review_count > 0 ? (
                    <div className="flex items-center gap-1">
                      <Star className="w-5 h-5 fill-yellow-400 text-yellow-400" />
                      <span className="font-semibold">{property.rating.toFixed(1)}</span>
                      <span>({property.review_count} reviews)</span>
                    </div>
                  ) : <span className="text-sm">No reviews yet</span>}
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
            <a href="#booking-panel" className="mb-4 inline-flex min-h-11 items-center rounded-lg bg-primary px-4 py-2 font-semibold text-white hover:bg-secondary">
              Check availability
            </a>
            <nav aria-label="Property sections" className="flex flex-wrap gap-2 border-y border-gray-200 py-3 text-sm">
              <a href="#about-section" className="rounded-full px-3 py-2 text-primary hover:bg-blue-50">About</a>
              {(!!villaUnit || (property.room_types?.length ?? 0) > 0) && (
                <a href="#rooms-section" className="rounded-full px-3 py-2 text-primary hover:bg-blue-50">Rooms</a>
              )}
              {property.amenities.length > 0 && (
                <a href="#amenities-section" className="rounded-full px-3 py-2 text-primary hover:bg-blue-50">Amenities</a>
              )}
              <a href="#reviews-section" className="rounded-full px-3 py-2 text-primary hover:bg-blue-50">Reviews</a>
              {locationQuery && (
                <a href="#location-section" className="rounded-full px-3 py-2 text-primary hover:bg-blue-50">Location</a>
              )}
            </nav>
          </div>

          {/* Entry Villa - the whole villa is the bookable unit: no room selection */}
          {isVilla && villaUnit && (
            <div id="rooms-section" className="mb-8 scroll-mt-24">
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
            <div id="rooms-section" className="mb-8 scroll-mt-24">
              <h2 className="text-2xl font-bold mb-4">Rooms</h2>
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
                        <div className="relative h-32 w-full sm:w-48 flex-shrink-0 rounded-lg overflow-hidden bg-gray-100">
                          {roomPhoto && !failedPhotoUrls.includes(roomPhoto.cloudinary_url || roomPhoto.url) ? (
                            <Image
                              src={roomPhoto.cloudinary_url || roomPhoto.url}
                              alt={`${room.name} at ${property.name}`}
                              fill
                              className="object-cover"
                              sizes="(max-width: 640px) 100vw, 192px"
                              onError={() => setFailedPhotoUrls((urls) => [...urls, roomPhoto.cloudinary_url || roomPhoto.url])}
                            />
                          ) : (
                            <div className="flex h-full items-center justify-center text-sm text-gray-500">
                              {roomPhoto ? 'Room photo unavailable' : 'No room photo'}
                            </div>
                          )}
                        </div>
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
                            {room.bed_configuration && <span>{room.bed_configuration}</span>}
                            {room.bathroom_type && <span>{room.bathroom_type.replace('_', ' ')} bathroom</span>}
                          </div>
                          {room.amenities && room.amenities.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-2">
                              {room.amenities.map((a: any) => (
                                <span key={a.id} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">{a.amenity_name || a.name}</span>
                              ))}
                            </div>
                          )}
                          <button
                            type="button"
                            onClick={() => setSelectedRoomTypeId(room.id)}
                            aria-pressed={isSelected}
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
            <div id="amenities-section" className="mb-8 scroll-mt-24">
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
          <div id="about-section" className="mb-8 scroll-mt-24">
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

          {locationQuery && (
            <section id="location-section" className="mb-8 scroll-mt-24" aria-labelledby="location-heading">
              <h2 id="location-heading" className="text-2xl font-bold mb-4">Location</h2>
              <p className="text-gray-600">
                {[property.address, property.city, property.district, property.province].filter(Boolean).join(', ')}
              </p>
              <a
                href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(locationQuery)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-lg border border-primary px-4 py-2 text-primary hover:bg-blue-50"
              >
                <MapPin className="h-4 w-4" />
                Open map
              </a>
            </section>
          )}

          <section id="reviews-section" className="mb-8 scroll-mt-24" aria-labelledby="reviews-heading">
            <h2 id="reviews-heading" className="text-2xl font-bold mb-4">Guest Reviews</h2>
            {reviewsLoading ? (
              <p className="text-gray-600" aria-live="polite">Loading reviews...</p>
            ) : reviewsError ? (
              <p className="text-sm text-red-700" role="alert">Unable to load reviews right now.</p>
            ) : reviews.length > 0 ? (
              <div className="space-y-4">
                {reviews.map((review) => (
                  <article key={review.id} className="rounded-lg border border-gray-200 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-semibold">{review.guest?.first_name || 'Guest'}</p>
                      <p className="flex items-center gap-1 text-sm" aria-label={`${review.rating} out of 5 stars`}>
                        <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                        {review.rating}/5
                      </p>
                    </div>
                    {review.title && <h3 className="mt-2 font-medium">{review.title}</h3>}
                    <p className="mt-2 whitespace-pre-wrap text-gray-600">{review.comment}</p>
                  </article>
                ))}
              </div>
            ) : (
              <p className="text-gray-600">No published reviews yet.</p>
            )}
          </section>

          {/* Contact Property */}
          {(propertyWhatsApp || property.contact?.email) && (
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-4">Contact This Property</h2>
              <div className="flex flex-wrap gap-3">
                {/* The property's published WhatsApp contact - opened as a link, never printed as text */}
                {propertyWhatsApp && (
                  <a
                    href={propertyWhatsApp}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-5 py-3 bg-green-50 text-green-700 rounded-lg font-medium hover:bg-green-100"
                  >
                    Contact Owner on WhatsApp
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
          <div id="booking-panel" className="card scroll-mt-24 p-5 sm:p-6 lg:sticky lg:top-20">
            {/* Price */}
            <div className="mb-6">
              <p className="text-gray-600 text-sm">{selectedRoom ? selectedRoom.name : 'Starting from'}</p>
              {sidebarPrice > 0 ? (
                <>
                  <p className="text-3xl font-bold text-primary">LKR {sidebarPrice.toLocaleString()}</p>
                  <p className="text-gray-600 text-sm">per night</p>
                </>
              ) : (
                <p className="text-lg font-semibold text-gray-500">Price not set</p>
              )}
            </div>

            {!selectedRoomTypeId && (
              <div className="mb-4 rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
                {isVilla ? 'This villa is not available for booking yet.' : 'Select a room above to continue booking.'}
              </div>
            )}

            {showBookingReview ? (
              <section aria-labelledby="booking-review-heading">
                <h2 id="booking-review-heading" className="mb-4 text-xl font-bold">Review your booking</h2>
                <dl className="space-y-3 rounded-lg bg-gray-50 p-4 text-sm">
                  <div><dt className="text-gray-600">Property</dt><dd className="font-semibold">{property.name}</dd></div>
                  <div><dt className="text-gray-600">Room</dt><dd className="font-semibold">{selectedRoom?.name || 'Selected room'}</dd></div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><dt className="text-gray-600">Check-in</dt><dd className="font-medium">{checkIn}</dd></div>
                    <div><dt className="text-gray-600">Check-out</dt><dd className="font-medium">{checkOut}</dd></div>
                  </div>
                  <div><dt className="text-gray-600">Guests</dt><dd className="font-medium">{guests} adult{guests === 1 ? '' : 's'}</dd></div>
                  <div><dt className="text-gray-600">Guest name</dt><dd className="font-medium">{guestName}</dd></div>
                  <div><dt className="text-gray-600">Email</dt><dd className="break-all font-medium">{user?.email || 'Email not available'}</dd></div>
                  <div><dt className="text-gray-600">WhatsApp / mobile</dt><dd className="font-medium">{guestPhone.trim()}</dd></div>
                </dl>

                {priceBreakdown && quoteIsCurrent && (
                  <div className="mt-4 space-y-2 border-t border-gray-200 pt-4 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Room ({priceBreakdown.nights} night{priceBreakdown.nights === 1 ? '' : 's'})</span>
                      <span>LKR {Number(priceBreakdown.room_subtotal).toLocaleString()}</span>
                    </div>
                    {Number(priceBreakdown.guest_fees) > 0 && (
                      <div className="flex justify-between"><span className="text-gray-600">Guest fees</span><span>LKR {Number(priceBreakdown.guest_fees).toLocaleString()}</span></div>
                    )}
                    {Number(priceBreakdown.discount) > 0 && (
                      <div className="flex justify-between"><span className="text-gray-600">Discount</span><span>-LKR {Number(priceBreakdown.discount).toLocaleString()}</span></div>
                    )}
                    <div className="flex justify-between"><span className="text-gray-600">Service fee</span><span>LKR {Number(priceBreakdown.service_fee).toLocaleString()}</span></div>
                    <div className="flex justify-between"><span className="text-gray-600">Tax</span><span>LKR {Number(priceBreakdown.tax).toLocaleString()}</span></div>
                    <div className="flex justify-between border-t border-gray-200 pt-2 text-lg font-bold">
                      <span>Total</span><span className="text-primary">LKR {Number(priceBreakdown.total).toLocaleString()}</span>
                    </div>
                  </div>
                )}
                <p className="mt-3 text-xs text-gray-500">
                  Availability and the final total are checked again by the booking service when you confirm.
                </p>
                <button
                  type="button"
                  onClick={() => setShowBookingReview(false)}
                  className="mt-4 w-full rounded-lg border border-gray-300 px-4 py-3 text-gray-700 hover:bg-gray-50"
                >
                  Edit booking details
                </button>
                <button
                  type="button"
                  onClick={() => void handleConfirmBooking()}
                  disabled={bookingLoading || calculating || !quoteIsCurrent || checkingAvailability || (availability !== null && !availability.available)}
                  className="mt-3 w-full btn-primary disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {bookingLoading ? 'Confirming booking...' : 'Confirm Booking'}
                </button>
              </section>
            ) : (
              <>
            {/* Booking Form */}
            <div className="space-y-4">
              <div>
                <label htmlFor="booking-check-in" className="block text-sm font-semibold mb-2">Check-in</label>
                <input
                  id="booking-check-in"
                  type="date"
                  value={checkIn}
                  min={new Date().toISOString().split('T')[0]}
                  onChange={(e) => { setCheckIn(e.target.value); setBookingError(null) }}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>

              <div>
                <label htmlFor="booking-check-out" className="block text-sm font-semibold mb-2">Check-out</label>
                <input
                  id="booking-check-out"
                  type="date"
                  value={checkOut}
                  min={checkIn || new Date().toISOString().split('T')[0]}
                  onChange={(e) => { setCheckOut(e.target.value); setBookingError(null) }}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>

              <div>
                <label htmlFor="booking-guests" className="block text-sm font-semibold mb-2">Guests</label>
                <input
                  id="booking-guests"
                  type="number"
                  min="1"
                  value={guests}
                  onChange={(e) => { setGuests(parseInt(e.target.value) || 1); setBookingError(null) }}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>

              <div>
                <label htmlFor="guest-phone" className="block text-sm font-semibold mb-2">
                  WhatsApp / Mobile Number <span className="text-red-600">*</span>
                </label>
                <input
                  id="guest-phone"
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  required
                  maxLength={30}
                  placeholder="e.g. 0771234567 or +94771234567"
                  value={guestPhone}
                  onChange={(e) => { setGuestPhone(e.target.value); setGuestPhoneTouched(true) }}
                  aria-invalid={guestPhoneTouched && !guestPhoneValid}
                  className={`w-full border rounded px-3 py-2 ${guestPhoneTouched && guestPhone && !guestPhoneValid ? 'border-red-400' : 'border-gray-300'}`}
                />
                {guestPhoneTouched && guestPhone && !guestPhoneValid ? (
                  <p className="mt-1 text-xs text-red-700">Enter a valid number, e.g. 0771234567 or +94771234567.</p>
                ) : (
                  <p className="mt-1 text-xs text-gray-500">Shared only with the property so they can contact you about this booking.</p>
                )}
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
            {availabilityError && (
              <p role="status" className="mt-4 rounded-lg bg-yellow-50 p-3 text-sm text-yellow-800">
                Availability could not be checked right now. It will be verified again before the booking is created.
              </p>
            )}

            {/* Price Breakdown */}
            {priceError ? (
              <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
                Unable to calculate the current price.
                <button type="button" onClick={() => setPriceRetry((retry) => retry + 1)} className="ml-2 font-semibold underline">
                  Recheck price
                </button>
              </div>
            ) : calculating ? (
              <p className="mt-4 text-sm text-gray-600" aria-live="polite">Checking current price...</p>
            ) : priceBreakdown && quoteIsCurrent ? (
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
            ) : null}

              </>
            )}

            {bookingError && (
              <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{bookingError}</div>
            )}

            {/* Book Button */}
            {!showBookingReview && (
              <>
                <button
                  type="button"
                  onClick={handleBooking}
                  disabled={!selectedRoomTypeId || !checkIn || !checkOut || bookingLoading || calculating || !quoteIsCurrent || checkingAvailability || (availability !== null && !availability.available)}
                  className="w-full btn-primary mt-6 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isAuthenticated ? 'Review Booking' : 'Sign in to Book'}
                </button>

                {!isAuthenticated && (
                  <p className="text-xs text-gray-600 mt-2 text-center">
                    <Link href={loginUrl(returnPath)} className="text-primary hover:underline">
                      Sign in
                    </Link>
                    {' '}to book this property
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
