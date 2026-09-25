/**
 * My Bookings page - list of user's reservations
 */

'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/stores/auth'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import { safeWhatsAppUrl } from '@/lib/whatsapp'
import type { Booking, BookingPaymentStatus } from '@/types'
import { Calendar, MapPin, DollarSign, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

// Booking statuses that still hold the rooms and may be paid
// (mirrors BookingService.PAYABLE_STATUSES - the backend re-checks anyway).
const PAYABLE_BOOKING_STATUSES = ['pending', 'payment_pending', 'confirmed']
// Payment states where a new online payment attempt makes no sense.
const SETTLED_PAYMENT_STATUSES: BookingPaymentStatus[] = ['paid', 'processing', 'refunded', 'partially_refunded']

const PAYMENT_STATUS_LABELS: Record<string, string> = {
  pending: 'Not paid',
  processing: 'Processing',
  paid: 'Paid',
  failed: 'Payment failed',
  cancelled: 'Payment cancelled',
  refunded: 'Refunded',
  partially_refunded: 'Partially refunded',
}

// After returning from Stripe, the webhook (not the browser) confirms the
// payment. Re-check the server for a short while before telling the guest
// it is still processing.
const RETURN_POLL_INTERVAL_MS = 3000
const RETURN_POLL_ATTEMPTS = 10

type ReturnNotice =
  | { kind: 'checking'; reference: string }
  | { kind: 'paid'; reference: string }
  | { kind: 'pending'; reference: string }
  | { kind: 'cancelled'; reference: string }

export default function BookingsPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading } = useAuth()
  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [cancellingId, setCancellingId] = useState<string | null>(null)
  const [payingId, setPayingId] = useState<string | null>(null)
  const [payErrors, setPayErrors] = useState<Record<string, string>>({})
  const [returnNotice, setReturnNotice] = useState<ReturnNotice | null>(null)
  const [createdReference, setCreatedReference] = useState<string | null>(null)
  const returnHandled = useRef(false)

  // Check authentication
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  // Load bookings (and, when returning from Stripe Checkout, poll the server
  // for the webhook-verified payment status)
  useEffect(() => {
    if (!isAuthenticated) return
    let cancelled = false
    let pollTimer: ReturnType<typeof setTimeout> | undefined

    // Read ?payment=success|cancelled&booking=REF once, then drop it from the
    // URL so a page refresh does not replay the notice. Read from
    // window.location (not useSearchParams) to stay static-export friendly.
    let returnParams: { payment: string; reference: string } | null = null
    if (!returnHandled.current && typeof window !== 'undefined') {
      returnHandled.current = true
      const params = new URLSearchParams(window.location.search)
      const payment = params.get('payment')
      const reference = params.get('booking')
      // Set by the property page right after a booking is created
      const created = params.get('booking_created')
      if ((payment === 'success' || payment === 'cancelled') && reference) {
        returnParams = { payment, reference }
      }
      if (created) setCreatedReference(created)
      if (returnParams || created) {
        window.history.replaceState(null, '', window.location.pathname)
      }
    }

    async function loadBookings(): Promise<Booking[] | null> {
      try {
        const data = await api.getBookings()
        if (!cancelled) setBookings(data)
        return data
      } catch (error) {
        console.error('Failed to load bookings:', error)
        return null
      }
    }

    async function init() {
      setLoading(true)
      const data = await loadBookings()
      if (!cancelled) setLoading(false)
      if (!returnParams || cancelled) return

      const { payment, reference } = returnParams
      if (payment === 'cancelled') {
        setReturnNotice({ kind: 'cancelled', reference })
        return
      }

      // Success URL return != verified payment: only the server's
      // payment_status (set by the verified Stripe webhook) counts.
      const isPaid = (list: Booking[] | null) =>
        !!list?.find((b) => b.booking_reference === reference && b.payment_status === 'paid')

      if (isPaid(data)) {
        setReturnNotice({ kind: 'paid', reference })
        return
      }
      setReturnNotice({ kind: 'checking', reference })

      let attempts = 0
      const poll = async () => {
        attempts += 1
        const latest = await loadBookings()
        if (cancelled) return
        if (isPaid(latest)) {
          setReturnNotice({ kind: 'paid', reference })
        } else if (attempts >= RETURN_POLL_ATTEMPTS) {
          setReturnNotice({ kind: 'pending', reference })
        } else {
          pollTimer = setTimeout(poll, RETURN_POLL_INTERVAL_MS)
        }
      }
      pollTimer = setTimeout(poll, RETURN_POLL_INTERVAL_MS)
    }

    init()
    return () => {
      cancelled = true
      if (pollTimer) clearTimeout(pollTimer)
    }
  }, [isAuthenticated])

  const canPayOnline = (booking: Booking) =>
    PAYABLE_BOOKING_STATUSES.includes(booking.status) &&
    !SETTLED_PAYMENT_STATUSES.includes(booking.payment_status)

  const handlePayOnline = async (booking: Booking) => {
    if (payingId) return // one checkout at a time - prevents duplicate clicks
    setPayingId(booking.id)
    setPayErrors((current) => ({ ...current, [booking.id]: '' }))

    try {
      // Only the booking id and method are sent - the backend charges the
      // server-side booking total and returns the hosted Checkout URL.
      const result = await api.initiatePayment({ booking_id: booking.id, payment_method: 'stripe' })
      const url = result.payment_url
      if (!url || !url.startsWith('https://')) {
        throw new Error('The payment page could not be opened. Please try again.')
      }
      // Leave payingId set: the browser is navigating away to Stripe.
      window.location.assign(url)
    } catch (err: any) {
      const data = err.response?.data
      setPayErrors((current) => ({
        ...current,
        [booking.id]: data?.error || data?.detail || err.message || 'Could not start the payment. Please try again.',
      }))
      setPayingId(null)
    }
  }

  const handleCancelBooking = async (bookingId: string) => {
    if (!confirm('Are you sure you want to cancel this booking?')) return

    try {
      setCancellingId(bookingId)
      await api.cancelBooking(bookingId)
      // Reload bookings
      const updated = await api.getBookings()
      setBookings(updated)
    } catch (error) {
      console.error('Failed to cancel booking:', error)
      alert('Failed to cancel booking')
    } finally {
      setCancellingId(null)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'confirmed':
      case 'paid':
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'cancelled':
        return <XCircle className="w-5 h-5 text-red-600" />
      case 'pending':
        return <AlertCircle className="w-5 h-5 text-yellow-600" />
      default:
        return <Clock className="w-5 h-5 text-gray-600" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'confirmed':
      case 'paid':
        return <span className="badge badge-success">{status}</span>
      case 'cancelled':
      case 'rejected':
        return <span className="badge badge-danger">{status}</span>
      case 'pending':
        return <span className="badge badge-warning">{status}</span>
      default:
        return <span className="badge">{status}</span>
    }
  }

  const canCancelBooking = (booking: Booking) => {
    return ['pending', 'confirmed', 'payment_pending'].includes(booking.status)
  }

  if (isLoading || !isAuthenticated) {
    return null
  }

  const createdBooking = createdReference
    ? bookings.find((b) => b.booking_reference === createdReference)
    : undefined
  const createdWhatsApp = safeWhatsAppUrl(createdBooking?.owner_whatsapp_url)

  return (
    <div className="container py-8">
      <h1 className="text-3xl font-bold mb-8">My Bookings</h1>

      {createdReference && (
        <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
          <p>
            Booking <strong>{createdReference}</strong> created. You can pay online below
            {createdWhatsApp ? ' or message the property owner on WhatsApp to confirm the details.' : '.'}
          </p>
          {createdWhatsApp && (
            <a
              href={createdWhatsApp}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-block rounded-lg bg-green-600 px-4 py-2 font-medium text-white hover:bg-green-700"
            >
              Contact Owner on WhatsApp
            </a>
          )}
        </div>
      )}

      {returnNotice && (
        <div
          className={`mb-6 rounded-lg border p-4 text-sm ${
            returnNotice.kind === 'paid'
              ? 'border-green-200 bg-green-50 text-green-800'
              : returnNotice.kind === 'cancelled'
                ? 'border-gray-200 bg-gray-50 text-gray-800'
                : 'border-yellow-200 bg-yellow-50 text-yellow-800'
          }`}
        >
          {returnNotice.kind === 'paid' && (
            <>Payment received for booking <strong>{returnNotice.reference}</strong>. Thank you!</>
          )}
          {returnNotice.kind === 'checking' && (
            <>Confirming your payment for booking <strong>{returnNotice.reference}</strong> with Stripe...</>
          )}
          {returnNotice.kind === 'pending' && (
            <>
              Your payment for booking <strong>{returnNotice.reference}</strong> is still being confirmed.
              This can take a few minutes - refresh this page later. You will also receive an email once it is confirmed.
            </>
          )}
          {returnNotice.kind === 'cancelled' && (
            <>Payment for booking <strong>{returnNotice.reference}</strong> was cancelled. You have not been charged - you can try again below.</>
          )}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12">
          <p className="text-gray-600">Loading your bookings...</p>
        </div>
      ) : bookings.length > 0 ? (
        <div className="space-y-4">
          {bookings.map((booking) => (
            <div key={booking.id} className="card p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Booking Info */}
                <div>
                  <p className="text-sm text-gray-600 mb-1">Booking Reference</p>
                  <p className="text-lg font-mono font-bold text-primary mb-4">
                    {booking.booking_reference}
                  </p>

                  <div className="space-y-3">
                    <div className="flex items-start gap-3">
                      <Calendar className="w-5 h-5 text-gray-600 mt-0.5" />
                      <div>
                        <p className="text-sm text-gray-600">Check-in</p>
                        <p className="font-semibold">{booking.check_in_date}</p>
                      </div>
                    </div>

                    <div className="flex items-start gap-3">
                      <Calendar className="w-5 h-5 text-gray-600 mt-0.5" />
                      <div>
                        <p className="text-sm text-gray-600">Check-out</p>
                        <p className="font-semibold">{booking.check_out_date}</p>
                      </div>
                    </div>

                    <div className="flex items-start gap-3">
                      <MapPin className="w-5 h-5 text-gray-600 mt-0.5" />
                      <div>
                        <p className="text-sm text-gray-600">Duration</p>
                        <p className="font-semibold">{booking.number_of_nights} nights</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Guest Info */}
                <div>
                  <p className="text-sm text-gray-600 mb-4">
                    Guests ({booking.number_of_adults + booking.number_of_children})
                  </p>
                  {booking.guests && booking.guests.length > 0 ? (
                    <div className="space-y-2">
                      {booking.guests.map((guest) => (
                        <div key={guest.id} className="text-sm">
                          <p className="font-semibold">
                            {guest.first_name} {guest.last_name}
                            {guest.is_primary_guest && <span className="text-xs text-gray-600"> (Primary)</span>}
                          </p>
                          <p className="text-gray-600">{guest.email}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-600">
                      {booking.number_of_adults} adult(s)
                      {booking.number_of_children > 0 && `, ${booking.number_of_children} child(ren)`}
                    </p>
                  )}
                </div>

                {/* Status & Price */}
                <div className="flex flex-col justify-between">
                  <div>
                    <p className="text-sm text-gray-600 mb-2">Status</p>
                    <div className="flex items-center gap-2 mb-4">
                      {getStatusIcon(booking.status)}
                      {getStatusBadge(booking.status)}
                    </div>

                    <p className="text-sm text-gray-600 mb-1">Payment Status</p>
                    <p className="text-sm font-semibold mb-6">
                      {PAYMENT_STATUS_LABELS[booking.payment_status] || booking.payment_status}
                    </p>
                  </div>

                  <div>
                    <p className="text-sm text-gray-600 mb-2">Total Price</p>
                    <p className="text-3xl font-bold text-primary mb-4">
                      LKR {booking.total_price.toLocaleString()}
                    </p>

                    <div className="space-y-2">
                      {canPayOnline(booking) && (
                        <>
                          <button
                            type="button"
                            onClick={() => handlePayOnline(booking)}
                            disabled={payingId !== null}
                            className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition disabled:opacity-50"
                          >
                            {payingId === booking.id ? 'Opening secure payment...' : 'Pay online'}
                          </button>
                          {payErrors[booking.id] && (
                            <p className="text-sm text-red-600">{payErrors[booking.id]}</p>
                          )}
                        </>
                      )}
                      {booking.payment_status === 'processing' && (
                        <p className="text-sm text-yellow-700">Your payment is being confirmed.</p>
                      )}

                      <Link
                        href={`/booking/${booking.id}`}
                        className="w-full block text-center px-4 py-2 bg-primary text-white rounded-lg hover:bg-secondary transition"
                      >
                        View Details
                      </Link>

                      {/* Owner's WhatsApp with a prefilled booking message - the number itself is never shown */}
                      {safeWhatsAppUrl(booking.owner_whatsapp_url) ? (
                        <a
                          href={safeWhatsAppUrl(booking.owner_whatsapp_url)!}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="w-full block text-center px-4 py-2 border border-green-600 text-green-700 rounded-lg hover:bg-green-50 transition"
                        >
                          Contact Owner on WhatsApp
                        </a>
                      ) : (
                        <p className="text-xs text-gray-500 text-center">The owner has not added a WhatsApp number yet.</p>
                      )}

                      {canCancelBooking(booking) && (
                        <button
                          onClick={() => handleCancelBooking(booking.id)}
                          disabled={cancellingId === booking.id}
                          className="w-full px-4 py-2 border border-red-600 text-red-600 rounded-lg hover:bg-red-50 transition disabled:opacity-50"
                        >
                          {cancellingId === booking.id ? 'Cancelling...' : 'Cancel Booking'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {booking.special_requests && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <p className="text-sm font-semibold mb-2">Special Requests</p>
                  <p className="text-gray-600">{booking.special_requests}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <Calendar className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 mb-6">You haven't made any bookings yet</p>
          <Link href="/search" className="btn-primary">
            Search Properties
          </Link>
        </div>
      )}
    </div>
  )
}
