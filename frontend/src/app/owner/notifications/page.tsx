'use client'
import { useEffect, useState } from 'react'
import { MailOpen } from 'lucide-react'
import { api } from '@/lib/api'
import type { Notification } from '@/types'

function timeAgo(isoDate: string) {
  const diffMs = Date.now() - new Date(isoDate).getTime()
  const minutes = Math.floor(diffMs / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`
  const days = Math.floor(hours / 24)
  return `${days} day${days === 1 ? '' : 's'} ago`
}

export default function OwnerNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadNotifications()
  }, [])

  const loadNotifications = async () => {
    try {
      setLoading(true)
      const data = await api.getNotifications()
      setNotifications(data)
      setError(null)
    } catch (err) {
      console.error('Failed to load notifications:', err)
      setError('Failed to load notifications')
    } finally {
      setLoading(false)
    }
  }

  const handleMarkAsRead = async (id: string) => {
    try {
      await api.markNotificationAsRead(id)
      setNotifications(current => current.map(n => (n.id === id ? { ...n, status: 'read' } : n)))
    } catch (err) {
      console.error('Failed to mark as read:', err)
    }
  }

  const handleMarkAllAsRead = async () => {
    try {
      await api.markAllNotificationsAsRead()
      setNotifications(current => current.map(n => ({ ...n, status: 'read' })))
    } catch (err) {
      console.error('Failed to mark all as read:', err)
    }
  }

  const unreadCount = notifications.filter(n => n.status !== 'read').length

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen"><p className="text-gray-600">Loading notifications...</p></div>
  }

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900">Notifications</h1>
          {unreadCount > 0 && <p className="text-gray-600 mt-2">{unreadCount} unread</p>}
        </div>
        {unreadCount > 0 && (
          <button onClick={handleMarkAllAsRead} className="px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium hover:bg-blue-100">
            Mark all as read
          </button>
        )}
      </div>

      {error && <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">{error}</div>}

      <div className="space-y-3">
        {notifications.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">No notifications yet.</div>
        ) : (
          notifications.map(n => (
            <div key={n.id} className={`p-4 rounded-lg border ${n.status !== 'read' ? 'bg-blue-50 border-blue-100' : 'bg-white'}`}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-gray-900">{n.title}</p>
                  <p className="text-sm text-gray-600 mt-1">{n.message}</p>
                  <p className="text-xs text-gray-500 mt-2">{timeAgo(n.created_at)}</p>
                </div>
                {n.status !== 'read' && (
                  <button onClick={() => handleMarkAsRead(n.id)} title="Mark as read" className="flex-shrink-0">
                    <MailOpen className="w-5 h-5 text-blue-600" />
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
