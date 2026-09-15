/**
 * Admin Users Management - View and manage all platform users
 */

'use client'

import { useEffect, useState } from 'react'
import {
  Users,
  Search,
  Filter,
  MoreVertical,
  UserPlus,
  Shield,
  Mail,
} from 'lucide-react'

interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  is_staff: boolean
  is_active: boolean
  date_joined: string
  role: 'super_admin' | 'property_owner' | 'guest'
}

export default function AdminUsers() {
  const [users] = useState<User[]>([])
  const [filteredUsers, setFilteredUsers] = useState<User[]>([])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'owner' | 'guest' | 'admin'>('all')

  useEffect(() => {
    let filtered = users

    if (filter !== 'all') {
      filtered = filtered.filter(u => {
        if (filter === 'admin') return u.is_staff
        if (filter === 'owner') return !u.is_staff && u.role === 'property_owner'
        if (filter === 'guest') return !u.is_staff && u.role === 'guest'
        return true
      })
    }

    if (search) {
      filtered = filtered.filter(
        u =>
          u.email.toLowerCase().includes(search.toLowerCase()) ||
          u.first_name.toLowerCase().includes(search.toLowerCase()) ||
          u.last_name.toLowerCase().includes(search.toLowerCase())
      )
    }

    setFilteredUsers(filtered)
  }, [users, filter, search])

  const getRoleBadge = (user: User) => {
    if (user.is_staff) {
      return <span className="px-3 py-1 bg-purple-100 text-purple-800 text-xs font-semibold rounded-full">Super Admin</span>
    }
    if (user.role === 'property_owner') {
      return <span className="px-3 py-1 bg-blue-100 text-blue-800 text-xs font-semibold rounded-full">Owner</span>
    }
    return <span className="px-3 py-1 bg-gray-100 text-gray-800 text-xs font-semibold rounded-full">Guest</span>
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900">User Management</h1>
        <p className="text-gray-600 mt-2">Manage all platform users and their roles</p>
      </div>

      {/* Search & Filter */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search by email or name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>
          <div className="flex gap-2">
            {(['all', 'admin', 'owner', 'guest'] as const).map((f) => (
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
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {filteredUsers.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Name
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Email
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Role
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">
                    Joined
                  </th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-gray-900">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-medium text-gray-900">
                        {user.first_name} {user.last_name}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <a href={`mailto:${user.email}`} className="text-blue-600 hover:text-blue-700 flex items-center gap-1">
                        <Mail className="w-4 h-4" />
                        {user.email}
                      </a>
                    </td>
                    <td className="px-6 py-4">{getRoleBadge(user)}</td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        user.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {new Date(user.date_joined).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="p-2 hover:bg-gray-100 rounded">
                        <MoreVertical className="w-4 h-4 text-gray-600" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No users found</p>
          </div>
        )}
      </div>
    </div>
  )
}
