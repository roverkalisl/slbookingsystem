/**
 * My Bookings page - list of user's reservations
 */

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/stores/auth'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import type { Booking } from '@/types'
import { Calendar, MapPin, DollarSign, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

export default function BookingsPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading } = useAuth()
  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [cancellingId, setCancellingId] = useState<string | null>(null)

  // Check authentication
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isAuthenticated, isLoading, router])

  // Load bookings
  useEffect(() => {
    if (!isAuthenticated) return

    async function loadBookings() {
      try {
        setLoading(true)
        const data = await api.getBookings()
        setBookings(data)
      } catch (error) {
        console.error('Failed to load bookings:', error)
      } finally {
        setLoading(false)
      }
    }

    loadBookings()
  }, [isAuthenticated])

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

  return (
    <div className="container py-8">
      <h1 className="text-3xl font-bold mb-8">My Bookings</h1>

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
                  <p className="text-sm text-gray-600 mb-4">Guests ({booking.guests.length})</p>
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
                    <p className="text-sm font-semibold capitalize mb-6">{booking.payment_status}</p>
                  </div>

                  <div>
                    <p className="text-sm text-gray-600 mb-2">Total Price</p>
                    <p className="text-3xl font-bold text-primary mb-4">
                      LKR {booking.total_price.toLocaleString()}
                    </p>

                    <div className="space-y-2">
                      <Link
                        href={`/booking/${booking.id}`}
                        className="w-full block text-center px-4 py-2 bg-primary text-white rounded-lg hover:bg-secondary transition"
                      >
                        View Details
                      </Link>

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
