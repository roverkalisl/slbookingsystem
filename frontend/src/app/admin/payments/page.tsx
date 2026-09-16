/**
 * Admin Payments Management
 */

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import { CreditCard, Search, Eye, DollarSign } from 'lucide-react'

interface AdminPayment {
  id: string
  booking_reference: string
  property_name: string
  guest_name: string
  guest_email: string
  amount: number
  status: string
  payment_method: string
  created_at: string
}

export default function AdminPayments() {
  const [payments, setPayments] = useState<AdminPayment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadPayments()
  }, [])

  const loadPayments = async () => {
    try {
      setLoading(true)
      const response = await api.getAdminPayments(undefined, undefined, undefined, 1, 100)
      setPayments(response.results || [])
    } catch (err) {
      setError('Failed to load payments')
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="flex items-center justify-center min-h-screen"><p>Loading payments...</p></div>

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Payment Management</h1>
        <p className="text-gray-600 mt-2">Monitor and manage all platform payments</p>
      </div>

      {error && <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800">{error}</div>}

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {payments.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold">Booking</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold">Property</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold">Amount</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold">Status</th>
                  <th className="px-6 py-4 text-left text-sm font-semibold">Date</th>
                  <th className="px-6 py-4 text-right text-sm font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {payments.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm">{p.booking_reference}</td>
                    <td className="px-6 py-4 font-medium">{p.property_name}</td>
                    <td className="px-6 py-4 font-semibold">${Number(p.amount).toFixed(2)}</td>
                    <td className="px-6 py-4"><span className="px-2 py-1 text-xs rounded bg-blue-100 text-blue-800">{p.status}</span></td>
                    <td className="px-6 py-4 text-sm">{new Date(p.created_at).toLocaleDateString()}</td>
                    <td className="px-6 py-4 text-right"><Link href={`/admin/payments/${p.id}`} className="text-blue-600">View</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12"><CreditCard className="w-12 h-12 text-gray-400 mx-auto mb-4" /><p className="text-gray-600">No payments found</p></div>
        )}
      </div>
    </div>
  )
}
