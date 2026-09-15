'use client'
import { useState } from 'react'
import { Bell, Trash2, MailOpen } from 'lucide-react'

export default function OwnerNotifications() {
  const [notifications] = useState([
    { id: '1', type: 'booking', title: 'New Booking', message: 'John Doe booked your property', time: '2 hours ago', read: false },
    { id: '2', type: 'review', title: 'New Review', message: 'Guest left a 5-star review', time: '1 day ago', read: true },
    { id: '3', type: 'payment', title: 'Payment Received', message: 'LKR 125,000 received from booking BK001', time: '3 days ago', read: true },
  ])

  return (
    <div>
      <div className="mb-8"><h1 className="text-4xl font-bold text-gray-900">Notifications</h1></div>
      <div className="space-y-3">{notifications.map(n => (<div key={n.id} className="p-4 rounded-lg border"><div className="flex items-start justify-between"><div><p className="font-semibold text-gray-900">{n.title}</p><p className="text-sm text-gray-600 mt-1">{n.message}</p><p className="text-xs text-gray-500 mt-2">{n.time}</p></div><div className="flex gap-2">{!n.read && <button><MailOpen className="w-5 h-5 text-blue-600" /></button>}<button><Trash2 className="w-5 h-5 text-red-600" /></button></div></div></div>))}</div>
    </div>
  )
}
