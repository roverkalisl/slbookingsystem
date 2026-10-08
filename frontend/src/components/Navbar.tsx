/**
 * Navigation bar component
 */

'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/stores/auth'
import { Menu, X, LogOut, User, Home } from 'lucide-react'
import { useState } from 'react'

export function Navbar() {
  const router = useRouter()
  const { user, isAuthenticated, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)

  const handleLogout = async () => {
    try {
      await logout()
      router.push('/login')
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  const closeMobileMenu = () => setIsOpen(false)

  return (
    <nav className="bg-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 text-2xl font-bold text-primary">
            <Home className="w-8 h-8" />
            SL Booking
          </Link>

          {/* Desktop Menu */}
          <div className="hidden md:flex items-center gap-8">
            <Link href="/" className="text-gray-600 hover:text-primary transition">
              Home
            </Link>
            <Link href="/search" className="text-gray-600 hover:text-primary transition">
              Search Properties
            </Link>

            {isAuthenticated && user ? (
              <>
                <Link href="/bookings" className="text-gray-600 hover:text-primary transition">
                  My Bookings
                </Link>
                {user.roles?.includes('property_owner') && (
                  <Link href="/owner/dashboard" className="text-gray-600 hover:text-primary transition">
                    Owner Dashboard
                  </Link>
                )}
                {user.roles?.includes('super_admin') && (
                  <Link href="/admin/dashboard" className="text-gray-600 hover:text-primary transition">
                    Admin Dashboard
                  </Link>
                )}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <User className="w-5 h-5" />
                    <span className="text-sm">{user.first_name}</span>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-2 px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition"
                  >
                    <LogOut className="w-5 h-5" />
                    Logout
                  </button>
                </div>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="px-4 py-2 text-primary border border-primary rounded-lg hover:bg-blue-50 transition"
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-secondary transition"
                >
                  Sign Up
                </Link>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button
            type="button"
            className="md:hidden rounded-lg p-2 text-gray-700 hover:bg-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
            aria-label={isOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={isOpen}
            aria-controls="mobile-navigation"
            onClick={() => setIsOpen(!isOpen)}
          >
            {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {isOpen && (
          <div id="mobile-navigation" className="md:hidden mt-4 space-y-1 border-t border-gray-100 pt-3">
            <Link href="/" onClick={closeMobileMenu} className="block rounded-lg px-3 py-3 text-gray-600 hover:bg-gray-50 hover:text-primary">
              Home
            </Link>
            <Link href="/search" onClick={closeMobileMenu} className="block rounded-lg px-3 py-3 text-gray-600 hover:bg-gray-50 hover:text-primary">
              Search Properties
            </Link>
            {isAuthenticated && user ? (
              <>
                <Link href="/bookings" onClick={closeMobileMenu} className="block rounded-lg px-3 py-3 text-gray-600 hover:bg-gray-50 hover:text-primary">
                  My Bookings
                </Link>
                {user.roles?.includes('property_owner') && (
                  <Link href="/owner/dashboard" onClick={closeMobileMenu} className="block rounded-lg px-3 py-3 text-gray-600 hover:bg-gray-50 hover:text-primary">
                    Owner Dashboard
                  </Link>
                )}
                {user.roles?.includes('super_admin') && (
                  <Link href="/admin/dashboard" onClick={closeMobileMenu} className="block rounded-lg px-3 py-3 text-gray-600 hover:bg-gray-50 hover:text-primary">
                    Admin Dashboard
                  </Link>
                )}
                <button
                  onClick={() => { closeMobileMenu(); void handleLogout() }}
                  className="w-full rounded-lg px-3 py-3 text-left text-red-600 hover:bg-red-50 hover:text-red-700"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link href="/login" onClick={closeMobileMenu} className="block rounded-lg px-3 py-3 text-primary hover:bg-blue-50">
                  Login
                </Link>
                <Link href="/register" onClick={closeMobileMenu} className="block rounded-lg px-3 py-3 text-primary hover:bg-blue-50">
                  Sign Up
                </Link>
              </>
            )}
          </div>
        )}
      </div>
    </nav>
  )
}
