/**
 * Owner Properties - List and manage properties
 */

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Property } from '@/types'
import {
  Plus,
  Edit2,
  Eye,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Clock,
  XCircle,
  Search,
} from 'lucide-react'

interface PropertyWithActions extends Property {
  canEdit?: boolean
  canDelete?: boolean
}

export default function OwnerProperties() {
  const [properties, setProperties] = useState<PropertyWithActions[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'draft' | 'pending' | 'approved'>('all')
  const [search, setSearch] = useState('')

  useEffect(() => {
    loadProperties()
  }, [])

  const loadProperties = async () => {
    try {
      setLoading(true)
      const response = await api.getOwnerProperties()
      const data = response.results || []

      // Add action permissions based on status
      const propsWithActions = data.map(prop => ({
        ...prop,
        canEdit: ['draft', 'rejected'].includes(prop.status || 'draft'),
        canDelete: prop.status === 'draft',
      }))

      setProperties(propsWithActions)
      setError(null)
    } catch (err) {
      console.error('Failed to load properties:', err)
      setError('Failed to load properties')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (propertyId: string) => {
    if (!confirm('Are you sure you want to delete this property?')) return

    try {
      await api.deleteProperty(propertyId)
      setProperties(properties.filter(p => p.id !== propertyId))
    } catch (err) {
      console.error('Failed to delete property:', err)
      alert('Failed to delete property')
    }
  }

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle2 className="w-5 h-5 text-green-600" />
      case 'pending_approval':
        return <Clock className="w-5 h-5 text-yellow-600" />
      case 'draft':
        return <AlertCircle className="w-5 h-5 text-gray-600" />
      case 'rejected':
        return <XCircle className="w-5 h-5 text-red-600" />
      default:
        return <AlertCircle className="w-5 h-5 text-gray-600" />
    }
  }

  const getStatusBadge = (status?: string) => {
    const baseClasses = 'text-xs font-semibold px-3 py-1 rounded-full'
    switch (status) {
      case 'approved':
        return `${baseClasses} bg-green-100 text-green-800`
      case 'pending_approval':
        return `${baseClasses} bg-yellow-100 text-yellow-800`
      case 'draft':
        return `${baseClasses} bg-gray-100 text-gray-800`
      case 'rejected':
        return `${baseClasses} bg-red-100 text-red-800`
      default:
        return `${baseClasses} bg-gray-100 text-gray-800`
    }
  }

  const filteredProperties = properties.filter(prop => {
    if (filter !== 'all') {
      const statusMap = {
        draft: 'draft',
        pending: 'pending_approval',
        approved: 'approved',
      }
      if (prop.status !== statusMap[filter as keyof typeof statusMap]) return false
    }

    if (search) {
      return (
        prop.name.toLowerCase().includes(search.toLowerCase()) ||
        prop.city.toLowerCase().includes(search.toLowerCase())
      )
    }

    return true
  })

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
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold text-gray-900">Properties</h1>
          <p className="text-gray-600 mt-2">Manage all your listed properties</p>
        </div>
        <Link
          href="/owner/properties/add"
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
        >
          <Plus className="w-5 h-5" />
          Add Property
        </Link>
      </div>

      {/* Search and Filter */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search properties..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="flex gap-2">
            {(['all', 'draft', 'pending', 'approved'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                  filter === f
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Properties List */}
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
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Rating
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Bookings
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
                        <p className="text-sm text-gray-600">
                          {property.city}, {property.district}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(property.status)}
                        <span className={getStatusBadge(property.status)}>
                          {(property.status || 'draft').replace('_', ' ').toUpperCase()}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {(property.average_rating || 0) > 0 ? (
                        <span className="text-sm text-gray-900">
                          ★ {(property.average_rating || 0).toFixed(1)} ({property.total_reviews || 0})
                        </span>
                      ) : (
                        <span className="text-sm text-gray-500">No reviews</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">-</td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/owner/properties/manage?propertyId=${encodeURIComponent(property.id)}`}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Manage"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                        {property.canEdit && (
                          <Link
                            href={`/owner/properties/${property.id}/edit`}
                            className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                            title="Edit"
                          >
                            <Edit2 className="w-4 h-4" />
                          </Link>
                        )}
                        {property.canDelete && (
                          <button
                            onClick={() => handleDelete(property.id)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
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
                <Building2Icon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 mb-4">No properties yet</p>
                <Link
                  href="/owner/properties/add"
                  className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg text-sm font-medium"
                >
                  Add Your First Property
                </Link>
              </>
            ) : (
              <p className="text-gray-600">No properties match your filter</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function Building2Icon({ className }: { className: string }) {
  return <svg className={className} fill="currentColor" viewBox="0 0 24 24"><path d="M13 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V9l-7-7zM5 20V4h8v7h7v9H5z" /></svg>
}
