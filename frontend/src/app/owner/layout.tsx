/**
 * Owner portal layout with sidebar navigation
 */

'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/stores/auth'
import {
  Home,
  Building2,
  Plus,
  Calendar,
  BookOpen,
  MessageSquare,
  TrendingUp,
  Bell,
  Settings,
  LogOut,
  Menu,
  X,
} from 'lucide-react'
import { useEffect, useState } from 'react'

interface NavItem {
  label: string
  href: string
  icon: React.ReactNode
  badge?: number
}

export default function OwnerLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, isAuthenticated, isLoading, logout } = useAuth()
  const router = useRouter()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (mounted && !isLoading && !isAuthenticated) {
      router.push('/login')
    }
    // Check if user is a property owner
    if (mounted && !isLoading && isAuthenticated && !user?.roles?.includes('property_owner')) {
      router.push('/search')
    }
  }, [isAuthenticated, isLoading, mounted, user, router])

  if (!mounted || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-600">Loading...</p>
      </div>
    )
  }

  if (!isAuthenticated || !user?.roles?.includes('property_owner')) {
    return null
  }

  const navItems: NavItem[] = [
    { label: 'Dashboard', href: '/owner/dashboard', icon: <Home className="w-5 h-5" /> },
    { label: 'Properties', href: '/owner/properties', icon: <Building2 className="w-5 h-5" /> },
    { label: 'Add Property', href: '/owner/properties/add', icon: <Plus className="w-5 h-5" /> },
    { label: 'Calendar', href: '/owner/calendar', icon: <Calendar className="w-5 h-5" /> },
    { label: 'Bookings', href: '/owner/bookings', icon: <BookOpen className="w-5 h-5" /> },
    { label: 'Messages', href: '/owner/messages', icon: <MessageSquare className="w-5 h-5" /> },
    { label: 'Reviews', href: '/owner/reviews', icon: <MessageSquare className="w-5 h-5" /> },
    { label: 'Earnings', href: '/owner/earnings', icon: <TrendingUp className="w-5 h-5" /> },
    { label: 'Notifications', href: '/owner/notifications', icon: <Bell className="w-5 h-5" /> },
    { label: 'Settings', href: '/owner/settings', icon: <Settings className="w-5 h-5" /> },
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
        } fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 text-white transition-transform lg:static lg:translate-x-0`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-800">
          <Link href="/owner/dashboard" className="text-xl font-bold">
            SL Booking
          </Link>
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
              className="flex items-center gap-3 px-6 py-3 text-sm hover:bg-gray-800 transition-colors"
              onClick={() => setSidebarOpen(false)}
            >
              {item.icon}
              <span className="flex-1">{item.label}</span>
              {item.badge && (
                <span className="bg-blue-600 text-xs font-semibold px-2 py-1 rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          ))}
        </nav>

        {/* User Profile */}
        <div className="border-t border-gray-800 p-6">
          <div className="mb-4">
            <p className="text-sm text-gray-400">Logged in as</p>
            <p className="font-semibold">{user?.first_name || user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors text-sm"
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
          <div className="flex-1" />
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
