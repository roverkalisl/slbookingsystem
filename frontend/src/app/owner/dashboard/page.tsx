/**
 * Owner Dashboard - Overview of properties, bookings, revenue, and notifications
 */

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import type { Property, Booking } from '@/types'
import {
  Building2,
  Clock,
  TrendingUp,
  Users,
  CheckCircle2,
  AlertCircle,
  Calendar,
  DollarSign,
} from 'lucide-react'

interface DashboardStats {
  totalProperties: number
  pendingProperties: number
  approvedProperties: number
  activeBookings: number
  todayCheckIns: number
  todayCheckOuts: number
  totalRevenue: number
  occupancyRate: number
}

export default function OwnerDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [properties, setProperties] = useState<Property[]>([])
  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true)

        // Load owner's properties
        const propsResponse = await api.getProperties()
        const propsData = propsResponse.results || []
        setProperties(propsData)

        // Calculate stats
        const draft = propsData.filter(p => p.status === 'draft').length
        const approved = propsData.filter(p => p.status === 'approved').length
        const pending = propsData.filter(p => p.status === 'pending_approval').length

        // TODO: Load bookings from API when endpoint is available
        setStats({
          totalProperties: propsData.length,
          pendingProperties: pending,
          approvedProperties: approved,
          activeBookings: 0,
          todayCheckIns: 0,
          todayCheckOuts: 0,
          totalRevenue: 0,
          occupancyRate: 0,
        })
      } catch (err) {
        console.error('Failed to load dashboard:', err)
        setError('Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [])

  const StatCard = ({
    icon: Icon,
    label,
    value,
    trend,
    color,
  }: {
    icon: React.ReactNode
    label: string
    value: string | number
    trend?: string
    color: string
  }) => (
    <div className="bg-white rounded-lg shadow p-6 border-l-4" style={{ borderColor: color }}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-gray-600 text-sm font-medium">{label}</p>
          <p className="text-3xl font-bold mt-2">{value}</p>
          {trend && <p className="text-sm text-green-600 mt-1">{trend}</p>}
        </div>
        <div className="p-3 rounded-lg" style={{ backgroundColor: `${color}15` }}>
          {Icon}
        </div>
      </div>
    </div>
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-600">Loading dashboard...</p>
      </div>
    )
  }

  return (
    <div>
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">Welcome back! Here's your property overview.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={<Building2 className="w-6 h-6" style={{ color: '#3B82F6' }} />}
          label="Total Properties"
          value={stats?.totalProperties || 0}
          color="#3B82F6"
        />
        <StatCard
          icon={<AlertCircle className="w-6 h-6" style={{ color: '#F59E0B' }} />}
          label="Pending Approval"
          value={stats?.pendingProperties || 0}
          color="#F59E0B"
        />
        <StatCard
          icon={<CheckCircle2 className="w-6 h-6" style={{ color: '#10B981' }} />}
          label="Active Properties"
          value={stats?.approvedProperties || 0}
          color="#10B981"
        />
        <StatCard
          icon={<Users className="w-6 h-6" style={{ color: '#8B5CF6' }} />}
          label="Active Bookings"
          value={stats?.activeBookings || 0}
          color="#8B5CF6"
        />
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          icon={<Calendar className="w-6 h-6" style={{ color: '#EC4899' }} />}
          label="Check-ins Today"
          value={stats?.todayCheckIns || 0}
          color="#EC4899"
        />
        <StatCard
          icon={<Calendar className="w-6 h-6" style={{ color: '#14B8A6' }} />}
          label="Check-outs Today"
          value={stats?.todayCheckOuts || 0}
          color="#14B8A6"
        />
        <StatCard
          icon={<DollarSign className="w-6 h-6" style={{ color: '#06B6D4' }} />}
          label="Total Revenue"
          value={`LKR ${(stats?.totalRevenue || 0).toLocaleString()}`}
          color="#06B6D4"
        />
        <StatCard
          icon={<TrendingUp className="w-6 h-6" style={{ color: '#F97316' }} />}
          label="Occupancy Rate"
          value={`${stats?.occupancyRate || 0}%`}
          color="#F97316"
        />
      </div>

      {/* Recent Properties Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Properties */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold">Recent Properties</h2>
            </div>
            <div className="divide-y">
              {properties.length > 0 ? (
                properties.slice(0, 5).map((property) => (
                  <div key={property.id} className="p-6 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900">{property.name}</h3>
                        <p className="text-sm text-gray-600 mt-1">
                          {property.city}, {property.district}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <span
                            className={`text-xs font-semibold px-2 py-1 rounded-full ${
                              property.status === 'approved'
                                ? 'bg-green-100 text-green-800'
                                : property.status === 'pending_approval'
                                ? 'bg-yellow-100 text-yellow-800'
                                : property.status === 'draft'
                                ? 'bg-gray-100 text-gray-800'
                                : property.status === 'rejected'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {property.status.replace('_', ' ').toUpperCase()}
                          </span>
                          {(property.average_rating || 0) > 0 && (
                            <span className="text-xs text-gray-600">
                              ★ {(property.average_rating || 0).toFixed(1)} ({property.total_reviews || 0} reviews)
                            </span>
                          )}
                        </div>
                      </div>
                      <Link
                        href={`/owner/properties/manage?propertyId=${encodeURIComponent(property.id)}`}
                        className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                      >
                        Manage →
                      </Link>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-6 text-center text-gray-500">
                  <p className="mb-4">No properties yet</p>
                  <Link
                    href="/owner/properties/add"
                    className="inline-block bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg text-sm font-medium"
                  >
                    Add Your First Property
                  </Link>
                </div>
              )}
            </div>
            {properties.length > 5 && (
              <div className="p-6 border-t border-gray-200">
                <Link
                  href="/owner/properties"
                  className="text-blue-600 hover:text-blue-700 font-medium text-sm"
                >
                  View All Properties →
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions & Alerts */}
        <div>
          {/* Quick Actions */}
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-bold">Quick Actions</h2>
            </div>
            <div className="divide-y">
              <Link
                href="/owner/properties/add"
                className="block p-4 hover:bg-gray-50 transition-colors"
              >
                <p className="font-medium text-gray-900">+ Add New Property</p>
                <p className="text-sm text-gray-600">Start listing a new property</p>
              </Link>
              <Link
                href="/owner/calendar"
                className="block p-4 hover:bg-gray-50 transition-colors"
              >
                <p className="font-medium text-gray-900">Manage Availability</p>
                <p className="text-sm text-gray-600">Update calendar and block dates</p>
              </Link>
              <Link
                href="/owner/bookings"
                className="block p-4 hover:bg-gray-50 transition-colors"
              >
                <p className="font-medium text-gray-900">View Bookings</p>
                <p className="text-sm text-gray-600">Manage upcoming reservations</p>
              </Link>
            </div>
          </div>

          {/* Alerts */}
          {(stats?.pendingProperties || 0) > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex gap-3">
                <AlertCircle className="w-5 h-5 text-yellow-600 flex-shrink-0" />
                <div>
                  <p className="font-semibold text-yellow-900">
                    {stats?.pendingProperties} Pending Approval
                  </p>
                  <p className="text-sm text-yellow-800 mt-1">
                    Your properties are awaiting admin review
                  </p>
                  <Link
                    href="/owner/properties"
                    className="text-yellow-700 hover:text-yellow-900 font-medium text-sm mt-2 inline-block"
                  >
                    View Details →
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
