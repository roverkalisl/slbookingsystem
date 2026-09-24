'use client'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import type { Booking } from '@/types'

/**
 * No payment settlement exists yet (spec explicitly defers payment gateway
 * integration), so these figures are booking revenue - the value of
 * confirmed/completed bookings - not money actually collected. Labeled as
 * such throughout rather than implying real payouts.
 */
export default function OwnerEarnings() {
  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getBookings()
      .then(setBookings)
      .catch((err) => { console.error('Failed to load bookings:', err); setError('Failed to load earnings data') })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen"><p className="text-gray-600">Loading...</p></div>
  }

  const countingStatuses = ['confirmed', 'paid', 'completed']
  const revenueBookings = bookings.filter(b => countingStatuses.includes(b.status))
  const confirmedCount = bookings.filter(b => b.status === 'confirmed' || b.status === 'paid').length
  const completedCount = bookings.filter(b => b.status === 'completed').length
  const pendingCount = bookings.filter(b => b.status === 'pending').length
  const grossBookingValue = revenueBookings.reduce((sum, b) => sum + Number(b.total_price), 0)

  const now = new Date()
  const thisMonthValue = revenueBookings
    .filter(b => {
      const d = new Date(b.created_at)
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
    })
    .reduce((sum, b) => sum + Number(b.total_price), 0)

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Earnings</h1>
        <p className="text-gray-600 mt-2">Booking revenue from your properties - not a payment settlement report (online payments are not yet enabled)</p>
      </div>

      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm">Gross Booking Value</p>
          <p className="text-3xl font-bold mt-2">LKR {grossBookingValue.toLocaleString()}</p>
          <p className="text-xs text-gray-400 mt-1">Confirmed + completed bookings</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm">This Month</p>
          <p className="text-3xl font-bold mt-2">LKR {thisMonthValue.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm">Confirmed Bookings</p>
          <p className="text-3xl font-bold mt-2">{confirmedCount}</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm">Completed Bookings</p>
          <p className="text-3xl font-bold mt-2">{completedCount}</p>
        </div>
      </div>

      {pendingCount > 0 && (
        <div className="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
          {pendingCount} booking{pendingCount === 1 ? '' : 's'} pending your confirmation - not counted in revenue above until confirmed.
        </div>
      )}

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-4">Bookings</h2>
        {bookings.length === 0 ? (
          <p className="text-gray-500">No bookings yet.</p>
        ) : (
          <div className="space-y-3">
            {bookings.map(b => (
              <div key={b.id} className="flex items-center justify-between p-3 border rounded">
                <div>
                  <p className="font-medium text-gray-900">{b.booking_reference}</p>
                  <p className="text-sm text-gray-600">{b.property_name} &middot; {b.check_in_date} &rarr; {b.check_out_date}</p>
                </div>
                <span className="px-2 py-1 text-xs rounded bg-gray-100 capitalize">{b.status}</span>
                <p className="font-semibold">LKR {Number(b.total_price).toLocaleString()}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
