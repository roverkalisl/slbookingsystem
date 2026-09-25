'use client'
import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { api } from '@/lib/api'
import { whatsappLink } from '@/lib/whatsapp'
import type { Booking } from '@/types'

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  confirmed: 'bg-green-100 text-green-800',
  paid: 'bg-green-100 text-green-800',
  completed: 'bg-blue-100 text-blue-800',
  cancelled: 'bg-gray-100 text-gray-600',
  rejected: 'bg-red-100 text-red-800',
}

export default function OwnerBookings() {
  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actioningId, setActioningId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    loadBookings()
  }, [])

  const loadBookings = async () => {
    try {
      setLoading(true)
      const data = await api.getBookings()
      setBookings(data)
      setError(null)
    } catch (err) {
      console.error('Failed to load bookings:', err)
      setError('Failed to load bookings')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async (id: string) => {
    setActioningId(id)
    try {
      const updated = await api.confirmBooking(id)
      setBookings(current => current.map(b => (b.id === id ? { ...b, ...updated } : b)))
    } catch (err: any) {
      alert(err.response?.data?.error || 'Unable to confirm booking')
    } finally {
      setActioningId(null)
    }
  }

  const handleReject = async (id: string) => {
    const reason = window.prompt('Reason for rejecting this booking (optional):') || ''
    setActioningId(id)
    try {
      const updated = await api.rejectBooking(id, reason)
      setBookings(current => current.map(b => (b.id === id ? { ...b, ...updated } : b)))
    } catch (err: any) {
      alert(err.response?.data?.error || 'Unable to reject booking')
    } finally {
      setActioningId(null)
    }
  }

  const filtered = bookings.filter(b => {
    if (filter !== 'all' && b.status !== filter) return false
    if (search) {
      const term = search.toLowerCase()
      return (
        b.booking_reference?.toLowerCase().includes(term) ||
        b.guest_name?.toLowerCase().includes(term) ||
        b.property_name?.toLowerCase().includes(term)
      )
    }
    return true
  })

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen"><p className="text-gray-600">Loading bookings...</p></div>
  }

  return (
    <div>
      <div className="mb-8"><h1 className="text-4xl font-bold text-gray-900">Bookings</h1><p className="text-gray-600 mt-2">Manage bookings for your properties</p></div>

      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <input type="text" placeholder="Search by reference, guest, or property..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg" />
          </div>
          <div className="flex gap-2 flex-wrap">
            {['all', 'pending', 'confirmed', 'completed', 'rejected', 'cancelled'].map(f => (
              <button key={f} onClick={() => setFilter(f)} className={`px-4 py-2 rounded-lg text-sm capitalize ${filter === f ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700'}`}>{f}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {filtered.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">No bookings found.</div>
        ) : (
          filtered.map(b => {
            const wa = whatsappLink(b.guest_phone, `Hi ${b.guest_name || ''}, regarding your booking ${b.booking_reference} at ${b.property_name || 'our property'}.`)
            return (
              <div key={b.id} className="bg-white rounded-lg shadow p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3">
                      <h3 className="font-bold text-gray-900">{b.booking_reference}</h3>
                      <span className={`px-2 py-1 text-xs rounded-full font-semibold capitalize ${STATUS_STYLES[b.status] || 'bg-gray-100 text-gray-700'}`}>{b.status}</span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{b.property_name} &middot; {b.room_type_name}</p>
                    <p className="text-sm text-gray-600">{b.check_in_date} &rarr; {b.check_out_date} &middot; {b.number_of_nights} night(s)</p>
                    <p className="text-sm text-gray-600 mt-1">Guest: {b.guest_name} {b.guest_email && <span className="text-gray-400">({b.guest_email})</span>}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-gray-900">LKR {Number(b.total_price).toLocaleString()}</p>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2 border-t pt-4">
                  {b.status === 'pending' && (
                    <>
                      <button
                        onClick={() => handleConfirm(b.id)}
                        disabled={actioningId === b.id}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => handleReject(b.id)}
                        disabled={actioningId === b.id}
                        className="px-4 py-2 bg-red-50 text-red-700 rounded-lg text-sm font-medium hover:bg-red-100 disabled:opacity-50"
                      >
                        Reject
                      </button>
                    </>
                  )}
                  {wa && (
                    <a href={wa} target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-green-50 text-green-700 rounded-lg text-sm font-medium hover:bg-green-100">
                      WhatsApp Guest
                    </a>
                  )}
                  {b.guest_email && (
                    <a href={`mailto:${b.guest_email}?subject=${encodeURIComponent(`Regarding booking ${b.booking_reference}`)}`} className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100">
                      Email Guest
                    </a>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
