'use client'
import { useState } from 'react'
import { MessageSquare, Search, Send } from 'lucide-react'

export default function OwnerMessages() {
  const [conversations] = useState([
    { id: '1', guestName: 'John Doe', lastMessage: 'When can I check in?', unread: 2, avatar: '👤' },
    { id: '2', guestName: 'Jane Smith', lastMessage: 'The room is perfect!', unread: 0, avatar: '👩' },
  ])

  return (
    <div>
      <div className="mb-8"><h1 className="text-4xl font-bold text-gray-900">Messages</h1></div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 bg-white rounded-lg shadow p-6">
          <div className="mb-4 relative"><Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" /><input type="text" placeholder="Search conversations..." className="w-full pl-10 pr-4 py-2 border rounded-lg" /></div>
          <div className="space-y-2">{conversations.map(c => (<button key={c.id} className="w-full p-3 text-left border rounded-lg hover:bg-blue-50"><div className="flex items-center gap-3"><span className="text-2xl">{c.avatar}</span><div className="flex-1"><p className="font-medium text-gray-900">{c.guestName}</p><p className="text-sm text-gray-600 truncate">{c.lastMessage}</p></div>{c.unread > 0 && <span className="bg-red-600 text-white text-xs px-2 py-1 rounded-full">{c.unread}</span>}</div></button>))}</div>
        </div>
        <div className="lg:col-span-2 bg-white rounded-lg shadow p-6 flex flex-col"><p className="text-center text-gray-600">Select a conversation to view messages</p></div>
      </div>
    </div>
  )
}
