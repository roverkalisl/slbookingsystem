/**
 * Admin Payments Management - View and manage payment transactions
 */

'use client'

import { useEffect, useState } from 'react'
import {
  CreditCard,
  Search,
  Filter,
  DollarSign,
  Calendar,
  MoreVertical,
  TrendingUp,
} from 'lucide-react'

interface Payment {
  id: string
  booking_id: string
  amount: number
  method: 'card' | 'bank_transfer' | 'pay_at_property'
  status: 'pending' | 'completed' | 'failed' | 'refunded'
  created_at: string
  guest_name: string
}

export default function AdminPayments() {
  const [payments] = useState<Payment[]>([])
  const [filteredPayments, setFilteredPayments] = useState<Payment[]>([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'pending' | 'completed' | 'failed' | 'refunded'>('all')

  useEffect(() => {
    let filtered = payments

    if (filter !== 'all') {
      filtered = filtered.filter(p => p.status === filter)
    }

    if (search) {
      filtered = filtered.filter(
        p =>
          p.guest_name.toLowerCase().includes(search.toLowerCase()) ||
          p.booking_id.toLowerCase().includes(search.toLowerCase())
      )
    }

    setFilteredPayments(filtered)
  }, [payments, filter, search])

  const getStatusBadge = (status: Payment['status']) => {
    const baseClasses = 'px-3 py-1 text-xs font-semibold rounded-full'
    switch (status) {
      case 'pending':
        return `${baseClasses} bg-yellow-100 text-yellow-800`
      case 'completed':
        return `${baseClasses} bg-green-100 text-green-800`
      case 'failed':
        return `${baseClasses} bg-red-100 text-red-800`
      case 'refunded':
        return `${baseClasses} bg-blue-100 text-blue-800`
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`
    }
  }

  const getMethodBadge = (method: Payment['method']) => {
    const colors = {
      card: 'bg-purple-100 text-purple-800',
      bank_transfer: 'bg-blue-100 text-blue-800',
      pay_at_property: 'bg-orange-100 text-orange-800',
    }
    return `px-2 py-1 text-xs font-semibold rounded ${colors[method] || 'bg-gray-100'}`
  }

  const totalRevenue = payments.reduce((sum, p) => sum + (p.status === 'completed' ? p.amount : 0), 0)
  const pendingPayments = payments.filter(p => p.status === 'pending').length
  const completedPayments = payments.filter(p => p.status === 'completed').length

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Payments Management</h1>
        <p className="text-gray-600 mt-2">View and manage payment transactions</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Total Revenue</p>
              <p className="text-3xl font-bold mt-2">LKR {totalRevenue.toLocaleString()}</p>
            </div>
            <div className="p-3 rounded-lg bg-green-100">
              <DollarSign className="w-6 h-6 text-green-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Completed</p>
              <p className="text-3xl font-bold mt-2">{completedPayments}</p>
            </div>
            <div className="p-3 rounded-lg bg-blue-100">
              <TrendingUp className="w-6 h-6 text-blue-600" />
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Pending</p>
              <p className="text-3xl font-bold mt-2 text-orange-600">{pendingPayments}</p>
            </div>
            <div className="p-3 rounded-lg bg-orange-100">
              <CreditCard className="w-6 h-6 text-orange-600" />
            </div>
          </div>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by guest or booking ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>
          <div className="flex gap-2">
            {(['all', 'pending', 'completed', 'failed', 'refunded'] as const).map((f) => (
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

      {/* Payments Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {filteredPayments.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Guest
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Booking ID
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Method
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Amount
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Date
                  </th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-gray-900">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredPayments.map((payment) => (
                  <tr key={payment.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-medium text-gray-900">{payment.guest_name}</p>
                    </td>
                    <td className="px-6 py-4">
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {payment.booking_id}
                      </code>
                    </td>
                    <td className="px-6 py-4">
                      <span className={getMethodBadge(payment.method)}>
                        {payment.method.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-semibold text-gray-900">
                        LKR {payment.amount.toLocaleString()}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <span className={getStatusBadge(payment.status)}>
                        {payment.status.charAt(0).toUpperCase() + payment.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 text-sm text-gray-600">
                        <Calendar className="w-4 h-4" />
                        {new Date(payment.created_at).toLocaleDateString()}
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
            <CreditCard className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No payments found</p>
          </div>
        )}
      </div>
    </div>
  )
}
