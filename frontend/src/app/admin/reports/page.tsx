/**
 * Admin Reports - Analytics and performance reports
 */

'use client'

import {
  BarChart3,
  TrendingUp,
  Users,
  Building2,
  BookOpen,
  DollarSign,
  Calendar,
} from 'lucide-react'

export default function AdminReports() {
  // Mock data for reports
  const monthlyRevenue = [
    { month: 'Jan', revenue: 125000, bookings: 45 },
    { month: 'Feb', revenue: 145000, bookings: 52 },
    { month: 'Mar', revenue: 160000, bookings: 58 },
    { month: 'Apr', revenue: 155000, bookings: 56 },
    { month: 'May', revenue: 180000, bookings: 65 },
    { month: 'Jun', revenue: 195000, bookings: 70 },
  ]

  const topProperties = [
    { id: 1, name: 'Luxury Villa - Colombo', revenue: 450000, bookings: 32, rating: 4.8 },
    { id: 2, name: 'Beach Resort - Mirissa', revenue: 380000, bookings: 28, rating: 4.7 },
    { id: 3, name: 'Mountain Retreat - Kandy', revenue: 320000, bookings: 24, rating: 4.6 },
    { id: 4, name: 'City Apartment - Colombo', revenue: 280000, bookings: 22, rating: 4.5 },
    { id: 5, name: 'Garden Cottage - Sigiriya', revenue: 240000, bookings: 18, rating: 4.4 },
  ]

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">Analytics & Reports</h1>
        <p className="text-gray-600 mt-2">Platform performance metrics and insights</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-600">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">YTD Revenue</p>
              <p className="text-3xl font-bold mt-2">LKR 1,545K</p>
              <p className="text-sm text-green-600 mt-1">↑ 12% from last year</p>
            </div>
            <DollarSign className="w-6 h-6 text-blue-600 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-600">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Total Bookings</p>
              <p className="text-3xl font-bold mt-2">373</p>
              <p className="text-sm text-green-600 mt-1">↑ 18% from last year</p>
            </div>
            <BookOpen className="w-6 h-6 text-green-600 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-purple-600">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Avg Occupancy</p>
              <p className="text-3xl font-bold mt-2">67%</p>
              <p className="text-sm text-green-600 mt-1">↑ 4% from last month</p>
            </div>
            <Calendar className="w-6 h-6 text-purple-600 opacity-20" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 border-l-4 border-orange-600">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Avg Rating</p>
              <p className="text-3xl font-bold mt-2">4.6★</p>
              <p className="text-sm text-green-600 mt-1">Excellent performance</p>
            </div>
            <TrendingUp className="w-6 h-6 text-orange-600 opacity-20" />
          </div>
        </div>
      </div>

      {/* Revenue & Bookings Chart */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-red-600" />
          Monthly Performance
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Month</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Revenue</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Bookings</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Avg/Booking</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {monthlyRevenue.map((row) => (
                <tr key={row.month} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-medium text-gray-900">{row.month}</td>
                  <td className="px-6 py-3">
                    <p className="text-gray-900 font-semibold">LKR {(row.revenue / 1000).toFixed(0)}K</p>
                    <div className="w-32 bg-gray-200 rounded-full h-2 mt-1">
                      <div
                        className="bg-green-500 h-2 rounded-full"
                        style={{ width: `${(row.revenue / 200000) * 100}%` }}
                      />
                    </div>
                  </td>
                  <td className="px-6 py-3 text-gray-900">{row.bookings}</td>
                  <td className="px-6 py-3 text-gray-900">
                    LKR {(row.revenue / row.bookings / 1000).toFixed(1)}K
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top Properties */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-red-600" />
          Top Performing Properties
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Property</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Revenue</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Bookings</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Rating</th>
                <th className="px-6 py-3 text-right text-sm font-semibold text-gray-900">Rank</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {topProperties.map((property, idx) => (
                <tr key={property.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3">
                    <p className="font-medium text-gray-900">{property.name}</p>
                  </td>
                  <td className="px-6 py-3">
                    <p className="text-gray-900 font-semibold">
                      LKR {(property.revenue / 1000).toFixed(0)}K
                    </p>
                  </td>
                  <td className="px-6 py-3 text-gray-900">{property.bookings}</td>
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-1">
                      <span className="text-sm font-semibold text-gray-900">
                        {property.rating}★
                      </span>
                      <div className="w-24 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-yellow-400 h-2 rounded-full"
                          style={{ width: `${(property.rating / 5) * 100}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-3 text-right">
                    <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-red-100 text-red-800 font-semibold text-sm">
                      {idx + 1}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Export Button */}
      <div className="mt-8 text-center">
        <button className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors">
          Export Report (PDF)
        </button>
      </div>
    </div>
  )
}
