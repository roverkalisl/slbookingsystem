/**
 * Super Admin Dashboard - Platform overview and KPIs
 */

'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import { loadDashboardStats, type DashboardStats } from '@/lib/adminDashboard'
import type { Property } from '@/types'
import {
  Users,
  Building2,
  BookOpen,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Clock,
  DollarSign,
  Activity,
  Eye,
} from 'lucide-react'

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  // A failed stats request is shown as an error - never as zero statistics
  const [statsError, setStatsError] = useState<string | null>(null)
  const [properties, setProperties] = useState<Property[]>([])
  const [pendingError, setPendingError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setStatsError(null)
    setPendingError(null)

    // Statistics and the pending list load independently: one failing must
    // not blank (or zero) the other.
    const [statsResult] = await Promise.all([
      loadDashboardStats(() => api.getAdminDashboardStats()),
      api.getAdminProperties('pending_approval')
        .then((pendingProps) => setProperties(pendingProps))
        .catch((error) => {
          console.error('Failed to load pending properties:', error)
          setProperties([])
          setPendingError('Pending properties could not be loaded.')
        }),
    ])
    setStats(statsResult.stats)
    if (statsResult.error) {
      console.error('Failed to load admin dashboard statistics:', statsResult.error)
      setStatsError(statsResult.error)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])

  const StatCard = ({
    icon: Icon,
    label,
    value,
    color,
    trend,
  }: {
    icon: React.ReactNode
    label: string
    value: string | number
    color: string
    trend?: string
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
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="text-gray-600 mt-2">Platform overview and key metrics</p>
      </div>

      {/* Statistics failed to load: say so - never show zeros as if the platform were empty */}
      {statsError && (
        <div role="alert" className="mb-8 rounded-lg border border-red-200 bg-red-50 p-6 text-red-800">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-6 h-6 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-semibold">Platform statistics are unavailable</p>
              <p className="text-sm mt-1">{statsError}</p>
            </div>
            <button
              type="button"
              onClick={() => loadDashboard()}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {stats && (
        <>
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatCard
              icon={<Users className="w-6 h-6" style={{ color: '#3B82F6' }} />}
              label="Total Users"
              value={stats.totalUsers}
              color="#3B82F6"
            />
            <StatCard
              icon={<Building2 className="w-6 h-6" style={{ color: '#10B981' }} />}
              label="Total Properties"
              value={stats.totalProperties}
              color="#10B981"
            />
            <StatCard
              icon={<Clock className="w-6 h-6" style={{ color: '#F59E0B' }} />}
              label="Pending Review"
              value={stats.pendingProperties}
              color="#F59E0B"
            />
            <StatCard
              icon={<CheckCircle2 className="w-6 h-6" style={{ color: '#8B5CF6' }} />}
              label="Active Properties"
              value={stats.approvedProperties}
              color="#8B5CF6"
            />
          </div>

          {/* Secondary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatCard
              icon={<BookOpen className="w-6 h-6" style={{ color: '#EC4899' }} />}
              label="Total Bookings"
              value={stats.totalBookings}
              color="#EC4899"
            />
            <StatCard
              icon={<Activity className="w-6 h-6" style={{ color: '#14B8A6' }} />}
              label="Active Bookings"
              value={stats.activeBookings}
              color="#14B8A6"
            />
            <StatCard
              icon={<DollarSign className="w-6 h-6" style={{ color: '#06B6D4' }} />}
              label="Platform Revenue"
              value={stats.platformRevenue === null ? 'Not available' : `LKR ${stats.platformRevenue.toLocaleString()}`}
              color="#06B6D4"
            />
            <StatCard
              icon={<TrendingUp className="w-6 h-6" style={{ color: '#F97316' }} />}
              label="Avg Rating"
              value={`${stats.averageRating.toFixed(1)}★`}
              color="#F97316"
            />
          </div>

          {/* Property page views (one per visitor per day; owner/admin views not counted) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <StatCard
              icon={<Eye className="w-6 h-6" style={{ color: '#6366F1' }} />}
              label="Total Property Views"
              value={stats.totalPropertyViews.toLocaleString()}
              color="#6366F1"
            />
            <StatCard
              icon={<Eye className="w-6 h-6" style={{ color: '#0EA5E9' }} />}
              label="Views Today"
              value={stats.propertyViewsToday.toLocaleString()}
              color="#0EA5E9"
            />
            <StatCard
              icon={<Eye className="w-6 h-6" style={{ color: '#84CC16' }} />}
              label="Views This Month"
              value={stats.propertyViewsThisMonth.toLocaleString()}
              color="#84CC16"
            />
          </div>
        </>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Pending Properties for Approval */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-bold">Pending Approval</h2>
              <Link
                href="/admin/properties"
                className="text-blue-600 hover:text-blue-700 text-sm font-medium"
              >
                View All →
              </Link>
            </div>

            {pendingError ? (
              <div role="alert" className="p-6 text-center text-red-700">
                <AlertCircle className="w-8 h-8 mx-auto mb-2" />
                <p>{pendingError}</p>
              </div>
            ) : properties.filter(p => p.status === 'pending_approval').length > 0 ? (
              <div className="divide-y">
                {properties
                  .filter(p => p.status === 'pending_approval')
                  .slice(0, 10)
                  .map((property) => (
                    <div key={property.id} className="p-6 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h3 className="font-semibold text-gray-900">{property.name}</h3>
                          <p className="text-sm text-gray-600 mt-1">
                            Owner: {property.owner?.email || 'N/A'}
                          </p>
                          <p className="text-sm text-gray-600">
                            {property.city}, {property.district}
                          </p>
                          <p className="text-xs text-gray-500 mt-2">
                            Submitted: {property.submitted_at
                              ? new Date(property.submitted_at).toLocaleDateString()
                              : 'N/A'}
                          </p>
                        </div>
                        <Link
                          href={`/admin/properties/${property.id}`}
                          className="ml-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
                        >
                          Review
                        </Link>
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="p-6 text-center text-gray-500">
                <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-2" />
                <p>No properties pending approval</p>
              </div>
            )}
          </div>

          {/* Most Viewed Properties (approved/public only) */}
          <div className="bg-white rounded-lg shadow mt-8">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold">Most Viewed Properties</h2>
            </div>
            {!stats ? (
              <div className="p-6 text-center text-gray-500">
                <p>View statistics are unavailable</p>
              </div>
            ) : stats.mostViewedProperties.length > 0 ? (
              <div className="divide-y">
                {stats.mostViewedProperties.map((item, index) => (
                  <div key={item.id} className="p-6 hover:bg-gray-50 transition-colors flex items-center justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-900">{index + 1}. {item.name}</h3>
                      <p className="text-sm text-gray-600 mt-1">{item.city}</p>
                      <p className="text-xs text-gray-500 mt-1 break-all">ID: {item.id}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold">{item.view_count.toLocaleString()}</p>
                      <p className="text-xs text-gray-500">views</p>
                    </div>
                    <Link
                      href={`/admin/properties/${item.id}`}
                      className="ml-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
                    >
                      View
                    </Link>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center text-gray-500">
                <p>No property views recorded yet</p>
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
                href="/admin/properties"
                className="block p-4 hover:bg-gray-50 transition-colors"
              >
                <p className="font-medium text-gray-900">📋 Review Properties</p>
                <p className="text-sm text-gray-600">Manage pending approvals</p>
              </Link>
              <Link
                href="/admin/users"
                className="block p-4 hover:bg-gray-50 transition-colors"
              >
                <p className="font-medium text-gray-900">👥 Manage Users</p>
                <p className="text-sm text-gray-600">View all users & owners</p>
              </Link>
              <Link
                href="/admin/bookings"
                className="block p-4 hover:bg-gray-50 transition-colors"
              >
                <p className="font-medium text-gray-900">📖 View Bookings</p>
                <p className="text-sm text-gray-600">Monitor all bookings</p>
              </Link>
              <Link
                href="/admin/settings"
                className="block p-4 hover:bg-gray-50 transition-colors"
              >
                <p className="font-medium text-gray-900">⚙️ System Settings</p>
                <p className="text-sm text-gray-600">Configure platform</p>
              </Link>
            </div>
          </div>

          {/* Platform Health (only with real statistics) */}
          {stats && (
          <div className="bg-white rounded-lg shadow">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-lg font-bold">Platform Health</h2>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-900">Pending Approvals</span>
                  <span className="text-sm font-bold text-orange-600">
                    {stats?.pendingProperties || 0}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-orange-500 h-2 rounded-full"
                    style={{ width: `${Math.min((stats?.pendingProperties || 0) * 10, 100)}%` }}
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-900">Approval Rate</span>
                  <span className="text-sm font-bold text-green-600">
                    {stats?.totalProperties
                      ? Math.round(((stats?.approvedProperties || 0) / stats?.totalProperties) * 100)
                      : 0}
                    %
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{
                      width: `${
                        stats?.totalProperties
                          ? ((stats?.approvedProperties || 0) / stats?.totalProperties) * 100
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
          )}
        </div>
      </div>
    </div>
  )
}
