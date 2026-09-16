/**
 * Admin Bookings Management - View and manage all platform bookings
 */

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import {
  BookOpen,
  Search,
  Filter,
  Calendar,
  User,
  DollarSign,
  Eye,
  Loader2,
} from 'lucide-react'

interface AdminBooking {
  id: string
  booking_reference: string
  property_name: string
  property_owner: string
  property_owner_email: string
  guest_name: string
  guest_email: string
  check_in_date: string
  check_out_date: string
  total_price: number
  status: 'pending' | 'confirmed' | 'cancelled' | 'completed'
  payment_status: 'pending' | 'processing' | 'paid' | 'failed' | 'refunded'
  created_at: string
}

export default function AdminBookings() {
  const [bookings, setBookings] = useState<AdminBooking[]>([])
  const [filteredBookings, setFilteredBookings] = useState<AdminBooking[]>([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'confirmed' | 'cancelled' | 'completed'>('all')
  const [paymentFilter, setPaymentFilter] = useState<'all' | 'pending' | 'paid' | 'failed'>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load bookings from API
  useEffect(() => {
    loadBookings()
  }, [])

  const loadBookings = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await api.getAdminBookings(undefined, undefined, undefined, 1, 100)
      setBookings(response.results || [])
    } catch (err) {
      console.error('Failed to load bookings:', err)
      setError('Failed to load bookings')
    } finally {
      setLoading(false)
    }
  }

  // Filter bookings
  useEffect(() => {
    let filtered = bookings

    if (statusFilter !== 'all') {
      filtered = filtered.filter(b => b.status === statusFilter)
    }

    if (paymentFilter !== 'all') {
      filtered = filtered.filter(b => b.payment_status === paymentFilter)
    }

    if (search) {
      filtered = filtered.filter(
        b =>
          b.booking_reference.toLowerCase().includes(search.toLowerCase()) ||
          b.property_name.toLowerCase().includes(search.toLowerCase()) ||
          b.guest_name.toLowerCase().includes(search.toLowerCase()) ||
          b.guest_email.toLowerCase().includes(search.toLowerCase())
      )
    }

    setFilteredBookings(filtered)
  }, [bookings, statusFilter, paymentFilter, search])

  const getStatusBadge = (status: AdminBooking['status']) => {
    const baseClasses = 'px-3 py-1 text-xs font-semibold rounded-full'
    switch (status) {
      case 'pending':
        return `${baseClasses} bg-yellow-100 text-yellow-800`
      case 'confirmed':
        return `${baseClasses} bg-blue-100 text-blue-800`
      case 'completed':
        return `${baseClasses} bg-green-100 text-green-800`
      case 'cancelled':
        return `${baseClasses} bg-red-100 text-red-800`
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`
    }
  }

  const getPaymentBadge = (status: AdminBooking['payment_status']) => {
    const baseClasses = 'px-3 py-1 text-xs font-semibold rounded-full'
    switch (status) {
      case 'pending':
        return `${baseClasses} bg-yellow-100 text-yellow-800`
      case 'paid':
        return `${baseClasses} bg-green-100 text-green-800`
      case 'processing':
        return `${baseClasses} bg-blue-100 text-blue-800`
      case 'failed':
        return `${baseClasses} bg-red-100 text-red-800`
      case 'refunded':
        return `${baseClasses} bg-purple-100 text-purple-800`
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-600">Loading bookings...</p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Bookings Management</h1>
        <p className="text-gray-600 mt-2">Monitor and manage all platform bookings</p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">
          {error}
        </div>
      )}

      {/* Search & Filter */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by booking reference, property, or guest..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>
          <div className="flex flex-col sm:flex-row gap-2 flex-wrap">
            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">Booking Status:</label>
              <div className="flex gap-2 flex-wrap">
                {(['all', 'pending', 'confirmed', 'cancelled', 'completed'] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setStatusFilter(f)}
                    className={`px-3 py-1 rounded-lg font-medium text-sm transition-colors flex items-center gap-2 ${
                      statusFilter === f
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    <Filter className="w-4 h-4" />
                    {f.charAt(0).toUpperCase() + f.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">Payment Status:</label>
              <div className="flex gap-2 flex-wrap">
                {(['all', 'pending', 'paid', 'failed'] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setPaymentFilter(f)}
                    className={`px-3 py-1 rounded-lg font-medium text-sm transition-colors flex items-center gap-2 ${
                      paymentFilter === f
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                    }`}
                  >
                    <DollarSign className="w-4 h-4" />
                    {f.charAt(0).toUpperCase() + f.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bookings Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {filteredBookings.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Booking Ref
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Property
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Owner
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Guest
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Dates
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Total
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Payment
                  </th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-gray-900">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredBookings.map((booking) => (
                  <tr key={booking.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {booking.booking_reference}
                      </code>
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-medium text-gray-900 text-sm">{booking.property_name}</p>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <p className="text-gray-900">{booking.property_owner}</p>
                      <p className="text-gray-600 text-xs">{booking.property_owner_email}</p>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <p className="text-gray-900">{booking.guest_name}</p>
                      <p className="text-gray-600 text-xs">{booking.guest_email}</p>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 text-sm text-gray-600">
                        <Calendar className="w-4 h-4" />
                        {new Date(booking.check_in_date).toLocaleDateString()} -{' '}
                        {new Date(booking.check_out_date).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 font-semibold text-gray-900">
                        <DollarSign className="w-4 h-4" />
                        {Number(booking.total_price).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={getStatusBadge(booking.status)}>
                        {booking.status.charAt(0).toUpperCase() + booking.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={getPaymentBadge(booking.payment_status)}>
                        {booking.payment_status.charAt(0).toUpperCase() + booking.payment_status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href={`/admin/bookings/${booking.id}`}
                        className="inline-flex items-center gap-2 px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <BookOpen className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No bookings found</p>
          </div>
        )}
      </div>
    </div>
  )
}
