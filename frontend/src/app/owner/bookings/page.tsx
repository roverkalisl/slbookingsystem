'use client'
import { useState } from 'react'
import { BookOpen, Search, Filter, Eye, Download } from 'lucide-react'

export default function OwnerBookings() {
  const [bookings] = useState([
    { id: 'BK001', guest: 'John Doe', checkIn: '2026-09-15', checkOut: '2026-09-20', status: 'confirmed', total: 125000 },
    { id: 'BK002', guest: 'Jane Smith', checkIn: '2026-09-22', checkOut: '2026-09-25', status: 'pending', total: 75000 },
  ])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all')

  return (
    <div>
      <div className="mb-8"><h1 className="text-4xl font-bold text-gray-900">Bookings</h1></div>
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative"><Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" /><input type="text" placeholder="Search bookings..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg" /></div>
          <div className="flex gap-2">{['all', 'pending', 'confirmed', 'completed'].map(f => (<button key={f} onClick={() => setFilter(f)} className={\px-4 py-2 rounded-lg \\}>{f}</button>))}</div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full"><thead className="bg-gray-50"><tr><th className="px-6 py-4 text-left text-sm font-semibold">Booking ID</th><th className="px-6 py-4 text-left">Guest</th><th className="px-6 py-4 text-left">Dates</th><th className="px-6 py-4 text-left">Status</th><th className="px-6 py-4 text-left">Total</th><th className="px-6 py-4">Actions</th></tr></thead><tbody className="divide-y">{bookings.map(b => (<tr key={b.id}><td className="px-6 py-4 font-medium">{b.id}</td><td className="px-6 py-4">{b.guest}</td><td className="px-6 py-4 text-sm">{b.checkIn} → {b.checkOut}</td><td className="px-6 py-4"><span className={\px-2 py-1 text-xs rounded \\}>{b.status}</span></td><td className="px-6 py-4 font-medium">LKR {b.total.toLocaleString()}</td><td className="px-6 py-4 text-right flex gap-2"><button><Eye className="w-4 h-4" /></button></td></tr>))}</tbody></table>
      </div>
    </div>
  )
}
