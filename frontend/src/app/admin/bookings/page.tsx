/**
 * Admin Bookings Management - View and manage all platform bookings
 */

'use client'

import { useEffect, useState } from 'react'
import {
  BookOpen,
  Search,
  Filter,
  Calendar,
  User,
  DollarSign,
  MoreVertical,
} from 'lucide-react'

interface Booking {
  id: string
  property_name: string
  guest_name: string
  check_in: string
  check_out: string
  status: 'pending' | 'confirmed' | 'cancelled' | 'completed'
  total_price: number
  created_at: string
}

export default function AdminBookings() {
  const [bookings] = useState<Booking[]>([])
  const [filteredBookings, setFilteredBookings] = useState<Booking[]>([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'pending' | 'confirmed' | 'cancelled' | 'completed'>('all')

  useEffect(() => {
    let filtered = bookings

    if (filter !== 'all') {
      filtered = filtered.filter(b => b.status === filter)
    }

    if (search) {
      filtered = filtered.filter(
        b =>
          b.property_name.toLowerCase().includes(search.toLowerCase()) ||
          b.guest_name.toLowerCase().includes(search.toLowerCase())
      )
    }

    setFilteredBookings(filtered)
  }, [bookings, filter, search])

  const getStatusBadge = (status: Booking['status']) => {
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

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Bookings Management</h1>
        <p className="text-gray-600 mt-2">Monitor and manage all platform bookings</p>
      </div>

      {/* Search & Filter */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by property or guest name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>
          <div className="flex gap-2">
            {(['all', 'pending', 'confirmed', 'cancelled', 'completed'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors flex items-center gap-2 whitespace-nowrap ${
                  filter === f
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
      </div>

      {/* Bookings Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {filteredBookings.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Property
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Guest
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Dates
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Total Price
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
                      <p className="font-medium text-gray-900">{booking.property_name}</p>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <User className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-900">{booking.guest_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <Calendar className="w-4 h-4" />
                        {new Date(booking.check_in).toLocaleDateString()} -{' '}
                        {new Date(booking.check_out).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={getStatusBadge(booking.status)}>
                        {booking.status.charAt(0).toUpperCase() + booking.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 font-semibold text-gray-900">
                        <DollarSign className="w-4 h-4" />
                        {booking.total_price.toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-2 hover:bg-gray-100 rounded">
                        <MoreVertical className="w-4 h-4 text-gray-600" />
                      </button>
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
