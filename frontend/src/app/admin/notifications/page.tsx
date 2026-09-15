/**
 * Admin Notifications & Logs - View system notifications and activity logs
 */

'use client'

import { useEffect, useState } from 'react'
import {
  Bell,
  Search,
  Filter,
  Clock,
  Mail,
  MessageSquare,
  AlertCircle,
  CheckCircle2,
  MoreVertical,
} from 'lucide-react'

interface Notification {
  id: string
  type: 'booking' | 'payment' | 'property' | 'system' | 'review'
  title: string
  message: string
  status: 'pending' | 'sent' | 'failed'
  recipient: string
  created_at: string
}

export default function AdminNotifications() {
  const [notifications] = useState<Notification[]>([])
  const [filteredNotifications, setFilteredNotifications] = useState<Notification[]>([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'booking' | 'payment' | 'property' | 'system' | 'review'>('all')
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'sent' | 'failed'>('all')

  useEffect(() => {
    let filtered = notifications

    if (filter !== 'all') {
      filtered = filtered.filter(n => n.type === filter)
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(n => n.status === statusFilter)
    }

    if (search) {
      filtered = filtered.filter(
        n =>
          n.title.toLowerCase().includes(search.toLowerCase()) ||
          n.recipient.toLowerCase().includes(search.toLowerCase()) ||
          n.message.toLowerCase().includes(search.toLowerCase())
      )
    }

    setFilteredNotifications(filtered)
  }, [notifications, filter, statusFilter, search])

  const getTypeIcon = (type: Notification['type']) => {
    switch (type) {
      case 'booking':
        return <MessageSquare className="w-4 h-4 text-blue-600" />
      case 'payment':
        return <Mail className="w-4 h-4 text-green-600" />
      case 'property':
        return <AlertCircle className="w-4 h-4 text-orange-600" />
      case 'review':
        return <Bell className="w-4 h-4 text-purple-600" />
      default:
        return <Bell className="w-4 h-4 text-gray-600" />
    }
  }

  const getStatusBadge = (status: Notification['status']) => {
    const baseClasses = 'px-3 py-1 text-xs font-semibold rounded-full flex items-center gap-1'
    switch (status) {
      case 'pending':
        return (
          <span className={`${baseClasses} bg-yellow-100 text-yellow-800`}>
            <Clock className="w-3 h-3" /> Pending
          </span>
        )
      case 'sent':
        return (
          <span className={`${baseClasses} bg-green-100 text-green-800`}>
            <CheckCircle2 className="w-3 h-3" /> Sent
          </span>
        )
      case 'failed':
        return (
          <span className={`${baseClasses} bg-red-100 text-red-800`}>
            <AlertCircle className="w-3 h-3" /> Failed
          </span>
        )
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`
    }
  }

  const totalNotifications = notifications.length
  const sentNotifications = notifications.filter(n => n.status === 'sent').length
  const failedNotifications = notifications.filter(n => n.status === 'failed').length
  const pendingNotifications = notifications.filter(n => n.status === 'pending').length

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Notifications & Logs</h1>
        <p className="text-gray-600 mt-2">Monitor system notifications and activity logs</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Total</p>
              <p className="text-3xl font-bold mt-2">{totalNotifications}</p>
            </div>
            <Bell className="w-6 h-6 text-gray-600 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Sent</p>
              <p className="text-3xl font-bold mt-2 text-green-600">{sentNotifications}</p>
            </div>
            <CheckCircle2 className="w-6 h-6 text-green-600 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Pending</p>
              <p className="text-3xl font-bold mt-2 text-yellow-600">{pendingNotifications}</p>
            </div>
            <Clock className="w-6 h-6 text-yellow-600 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Failed</p>
              <p className="text-3xl font-bold mt-2 text-red-600">{failedNotifications}</p>
            </div>
            <AlertCircle className="w-6 h-6 text-red-600 opacity-20" />
          </div>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col lg:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by title, recipient, or message..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            {(['all', 'booking', 'payment', 'property', 'system', 'review'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-2 rounded-lg font-medium text-sm transition-colors flex items-center gap-2 ${
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
        <div className="flex gap-2 mt-4 flex-wrap">
          {(['all', 'pending', 'sent', 'failed'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-2 rounded-lg font-medium text-sm transition-colors ${
                statusFilter === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {s === 'all' ? 'All Status' : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Notifications Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {filteredNotifications.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Type
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Title
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Recipient
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Sent
                  </th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-gray-900">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredNotifications.map((notification) => (
                  <tr key={notification.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {getTypeIcon(notification.type)}
                        <span className="text-sm font-medium text-gray-900">
                          {notification.type.charAt(0).toUpperCase() + notification.type.slice(1)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-medium text-gray-900">{notification.title}</p>
                      <p className="text-sm text-gray-600 line-clamp-2">{notification.message}</p>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {notification.recipient}
                    </td>
                    <td className="px-6 py-4">
                      {getStatusBadge(notification.status)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {new Date(notification.created_at).toLocaleDateString()}
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
            <Bell className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No notifications found</p>
          </div>
        )}
      </div>
    </div>
  )
}
