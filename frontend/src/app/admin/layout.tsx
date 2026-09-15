/**
 * Admin portal layout with sidebar navigation
 */

'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/stores/auth'
import {
  Home,
  Building2,
  Users,
  BookOpen,
  CreditCard,
  Bell,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  Shield,
} from 'lucide-react'
import { useEffect, useState } from 'react'

interface NavItem {
  label: string
  href: string
  icon: React.ReactNode
}

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, isAuthenticated, logout } = useAuth()
  const router = useRouter()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (mounted && !isAuthenticated) {
      router.push('/login')
    }
    // Check if user is super admin
    if (mounted && isAuthenticated && !user?.is_staff) {
      router.push('/')
    }
  }, [isAuthenticated, mounted, user, router])

  if (!mounted || !isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-600">Loading...</p>
      </div>
    )
  }

  const navItems: NavItem[] = [
    { label: 'Dashboard', href: '/admin/dashboard', icon: <Home className="w-5 h-5" /> },
    { label: 'Properties', href: '/admin/properties', icon: <Building2 className="w-5 h-5" /> },
    { label: 'Users', href: '/admin/users', icon: <Users className="w-5 h-5" /> },
    { label: 'Bookings', href: '/admin/bookings', icon: <BookOpen className="w-5 h-5" /> },
    { label: 'Payments', href: '/admin/payments', icon: <CreditCard className="w-5 h-5" /> },
    { label: 'Notifications', href: '/admin/notifications', icon: <Bell className="w-5 h-5" /> },
    { label: 'Reports', href: '/admin/reports', icon: <BarChart3 className="w-5 h-5" /> },
    { label: 'Settings', href: '/admin/settings', icon: <Settings className="w-5 h-5" /> },
  ]

  const handleLogout = async () => {
    try {
      await logout()
      router.push('/')
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } fixed inset-y-0 left-0 z-50 w-64 bg-red-900 text-white transition-transform lg:static lg:translate-x-0`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-red-800">
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6" />
            <span className="font-bold text-lg">Admin Panel</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-6">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-6 py-3 text-sm hover:bg-red-800 transition-colors"
              onClick={() => setSidebarOpen(false)}
            >
              {item.icon}
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        {/* User Profile */}
        <div className="border-t border-red-800 p-6">
          <div className="mb-4">
            <p className="text-xs text-red-200">Logged in as</p>
            <p className="font-semibold text-sm">{user?.email}</p>
            <p className="text-xs text-red-200">Super Admin</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-4 py-2 rounded-lg bg-red-800 hover:bg-red-700 transition-colors text-sm"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <div className="h-16 bg-white border-b border-gray-200 flex items-center px-6">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex-1 flex items-center gap-4">
            <h1 className="text-xl font-bold text-gray-900">SL Booking Admin</h1>
          </div>
          <div className="flex items-center gap-4">
            <button className="p-2 hover:bg-gray-100 rounded-lg">
              <Bell className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-7xl mx-auto px-4 py-8">
            {children}
          </div>
        </div>
      </div>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 lg:hidden z-40"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  )
}
