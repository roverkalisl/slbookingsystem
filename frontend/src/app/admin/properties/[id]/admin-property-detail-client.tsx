'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Property } from '@/types'
import { ArrowLeft, CheckCircle2, XCircle, Loader2 } from 'lucide-react'

export default function AdminPropertyDetailClient({ propertyId }: { propertyId: string }) {
  const router = useRouter()
  const [property, setProperty] = useState<Property | null>(null)
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState<'approve' | 'reject' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [rejectionReason, setRejectionReason] = useState('')

  useEffect(() => {
    const loadProperty = async () => {
      try {
        const response = await api.getProperties()
        const found = (response.results || []).find((item) => item.id.toString() === propertyId)
        if (!found) setError('Property not found')
        else setProperty(found)
      } catch {
        setError('Failed to load property')
      } finally {
        setLoading(false)
      }
    }
    loadProperty()
  }, [propertyId])

  const approve = async () => {
    if (!property) return
    try {
      setAction('approve')
      await api.approveProperty(property.id)
      router.push('/admin/properties?status=approved')
    } catch {
      setError('Failed to approve property')
      setAction(null)
    }
  }

  const reject = async () => {
    if (!property || !rejectionReason.trim()) {
      setError('Please provide a rejection reason')
      return
    }
    try {
      setAction('reject')
      await api.rejectProperty(property.id, rejectionReason)
      router.push('/admin/properties?status=rejected')
    } catch {
      setError('Failed to reject property')
      setAction(null)
    }
  }

  if (loading) return <div className="py-12 text-center text-gray-600">Loading property details...</div>
  if (!property) return <div className="py-12 text-center text-red-700">{error || 'Property not found'}</div>

  return (
    <div>
      <Link href="/admin/properties" className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-6">
        <ArrowLeft className="w-4 h-4" /> Back to Properties
      </Link>
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h1 className="text-3xl font-bold text-gray-900">{property.name}</h1>
        <p className="text-gray-600 mt-2">{property.short_description}</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          <div><p className="text-sm text-gray-600">Status</p><p className="font-semibold mt-1">{property.status}</p></div>
          <div><p className="text-sm text-gray-600">City</p><p className="font-semibold mt-1">{property.city}</p></div>
          <div><p className="text-sm text-gray-600">Bedrooms</p><p className="font-semibold mt-1">{property.bedrooms}</p></div>
          <div><p className="text-sm text-gray-600">Guests</p><p className="font-semibold mt-1">{property.max_guests}</p></div>
        </div>
      </div>
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-3">Description</h2>
        <p className="text-gray-700 whitespace-pre-line">{property.description}</p>
        {error && <p className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {property.status === 'pending_approval' && (
          <div className="mt-6 space-y-3 border-t pt-6">
            <button onClick={approve} disabled={Boolean(action)} className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-3 font-medium text-white disabled:opacity-50">
              {action === 'approve' ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Approve Property
            </button>
            <textarea value={rejectionReason} onChange={(event) => setRejectionReason(event.target.value)} rows={3} placeholder="Rejection reason" className="w-full rounded-lg border border-gray-300 p-3" />
            <button onClick={reject} disabled={Boolean(action)} className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-3 font-medium text-white disabled:opacity-50">
              {action === 'reject' ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />} Reject Property
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
