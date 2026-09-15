'use client'
import { useState } from 'react'
import { DollarSign, TrendingUp } from 'lucide-react'

export default function OwnerEarnings() {
  const [earnings] = useState({
    thisMonth: 125000,
    lastMonth: 95000,
    total: 425000,
    pending: 25000,
  })
  const [transactions] = useState([
    { id: '1', date: '2026-09-10', amount: 25000, status: 'completed', booking: 'BK001' },
    { id: '2', date: '2026-09-15', amount: 15000, status: 'pending', booking: 'BK002' },
  ])

  return (
    <div>
      <div className="mb-8"><h1 className="text-4xl font-bold text-gray-900">Earnings</h1></div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6"><p className="text-gray-600">This Month</p><p className="text-3xl font-bold mt-2">LKR {earnings.thisMonth.toLocaleString()}</p></div>
        <div className="bg-white rounded-lg shadow p-6"><p className="text-gray-600">Last Month</p><p className="text-3xl font-bold mt-2">LKR {earnings.lastMonth.toLocaleString()}</p></div>
        <div className="bg-white rounded-lg shadow p-6"><p className="text-gray-600">Total Earnings</p><p className="text-3xl font-bold mt-2">LKR {earnings.total.toLocaleString()}</p></div>
        <div className="bg-white rounded-lg shadow p-6"><p className="text-gray-600">Pending</p><p className="text-3xl font-bold mt-2 text-orange-600">LKR {earnings.pending.toLocaleString()}</p></div>
      </div>

      <div className="bg-white rounded-lg shadow p-6"><h2 className="text-xl font-bold mb-4">Recent Transactions</h2><div className="space-y-3">{transactions.map(t => (<div key={t.id} className="flex items-center justify-between p-3 border rounded"><div><p className="font-medium text-gray-900">{t.booking}</p><p className="text-sm text-gray-600">{t.date}</p></div><span className="px-2 py-1 text-xs rounded bg-gray-100">{t.status}</span><p className="font-semibold">LKR {t.amount.toLocaleString()}</p></div>))}</div></div>
    </div>
  )
}
