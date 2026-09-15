/**
 * Admin Property Approval Queue - Review and approve/reject properties
 */

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Property } from '@/types'
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Eye,
  Filter,
  Search,
  Clock,
} from 'lucide-react'

interface PropertyWithActions extends Property {
  isPending?: boolean
}

export default function AdminProperties() {
  const [properties, setProperties] = useState<PropertyWithActions[]>([])
  const [filteredProperties, setFilteredProperties] = useState<PropertyWithActions[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'pending' | 'all'>('pending')
  const [search, setSearch] = useState('')

  useEffect(() => {
    loadProperties()
  }, [])

  const loadProperties = async () => {
    try {
      setLoading(true)
      const response = await api.getProperties()
      const data = (response.results || []).map(prop => ({
        ...prop,
        isPending: prop.status === 'pending_approval',
      }))
      setProperties(data)
    } catch (error) {
      console.error('Failed to load properties:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let filtered = properties

    // Filter by status
    if (filter === 'pending') {
      filtered = filtered.filter(p => p.status === 'pending_approval')
    }

    // Filter by search
    if (search) {
      filtered = filtered.filter(
        p =>
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          p.owner?.email?.toLowerCase().includes(search.toLowerCase()) ||
          p.city.toLowerCase().includes(search.toLowerCase())
      )
    }

    setFilteredProperties(filtered)
  }, [properties, filter, search])

  const getStatusBadge = (status?: string) => {
    const baseClasses = 'text-xs font-semibold px-3 py-1 rounded-full'
    switch (status) {
      case 'pending_approval':
        return `${baseClasses} bg-yellow-100 text-yellow-800`
      case 'approved':
        return `${baseClasses} bg-green-100 text-green-800`
      case 'rejected':
        return `${baseClasses} bg-red-100 text-red-800`
      case 'draft':
        return `${baseClasses} bg-gray-100 text-gray-800`
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-600">Loading properties...</p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Property Approval Queue</h1>
        <p className="text-gray-600 mt-2">Review and approve/reject properties submitted by owners</p>
      </div>

      {/* Search & Filter */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by property name, owner email, or city..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>
          <div className="flex gap-2">
            {(['pending', 'all'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors flex items-center gap-2 ${
                  filter === f
                    ? 'bg-red-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                <Filter className="w-4 h-4" />
                {f === 'pending' ? 'Pending' : 'All'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Properties Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {filteredProperties.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Property
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Owner
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Location
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Submitted
                  </th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-gray-900">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredProperties.map((property) => (
                  <tr key={property.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <h3 className="font-semibold text-gray-900">{property.name}</h3>
                        <p className="text-sm text-gray-600">{property.short_description}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{property.owner?.first_name} {property.owner?.last_name}</p>
                        <p className="text-sm text-gray-600">{property.owner?.email}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {property.city}, {property.district}
                    </td>
                    <td className="px-6 py-4">
                      <span className={getStatusBadge(property.status)}>
                        {(property.status || 'draft').replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {property.submitted_at
                        ? new Date(property.submitted_at).toLocaleDateString()
                        : '—'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href={`/admin/properties/${property.id}`}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                        Review
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            {properties.length === 0 ? (
              <>
                <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">No properties found</p>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
                <p className="text-gray-600">No pending properties</p>
              </>
            )}
          </div>
        )}
      </div>

      {/* Stats Footer */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Pending Review</p>
              <p className="text-3xl font-bold mt-2 text-orange-600">
                {properties.filter(p => p.status === 'pending_approval').length}
              </p>
            </div>
            <Clock className="w-12 h-12 text-orange-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Approved</p>
              <p className="text-3xl font-bold mt-2 text-green-600">
                {properties.filter(p => p.status === 'approved').length}
              </p>
            </div>
            <CheckCircle2 className="w-12 h-12 text-green-500 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Rejected</p>
              <p className="text-3xl font-bold mt-2 text-red-600">
                {properties.filter(p => p.status === 'rejected').length}
              </p>
            </div>
            <XCircle className="w-12 h-12 text-red-500 opacity-20" />
          </div>
        </div>
      </div>
    </div>
  )
}
