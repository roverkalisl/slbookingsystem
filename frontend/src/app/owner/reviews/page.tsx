'use client'
import { useState } from 'react'
import { Star, MessageCircle } from 'lucide-react'

export default function OwnerReviews() {
  const [reviews] = useState([
    { id: '1', guestName: 'John Doe', rating: 5, comment: 'Excellent property and great host!', date: '2026-09-10', responded: false },
    { id: '2', guestName: 'Jane Smith', rating: 4, comment: 'Beautiful views but noisy neighborhood', date: '2026-09-08', responded: true },
  ])

  return (
    <div>
      <div className="mb-8"><h1 className="text-4xl font-bold text-gray-900">Reviews</h1></div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6 text-center"><p className="text-4xl font-bold text-yellow-500">4.8★</p><p className="text-gray-600 mt-2">Average Rating</p></div>
        <div className="bg-white rounded-lg shadow p-6 text-center"><p className="text-4xl font-bold text-gray-900">24</p><p className="text-gray-600 mt-2">Total Reviews</p></div>
        <div className="bg-white rounded-lg shadow p-6 text-center"><p className="text-4xl font-bold text-blue-600">18</p><p className="text-gray-600 mt-2">Responded</p></div>
      </div>

      <div className="space-y-4">{reviews.map(r => (<div key={r.id} className="bg-white rounded-lg shadow p-6"><div className="flex items-start justify-between mb-3"><div><p className="font-semibold text-gray-900">{r.guestName}</p><div className="flex gap-1 mt-1">{[...Array(r.rating)].map((_, i) => (<Star key={i} className="w-4 h-4 fill-yellow-500 text-yellow-500" />))}</div></div><span className="text-xs text-gray-600">{r.date}</span></div><p className="text-gray-700">{r.comment}</p></div>))}</div>
    </div>
  )
}
