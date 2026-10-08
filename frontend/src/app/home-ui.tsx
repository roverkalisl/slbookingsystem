/**
 * Home page - Hero + Featured Properties
 */

'use client'

import { useEffect, useState, type FormEvent } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { PropertyCard } from '@/components/PropertyCard'
import { api } from '@/lib/api'
import type { Property } from '@/types'
import { Search, MapPin, Calendar, Users } from 'lucide-react'

export default function Home() {
  const router = useRouter()
  const [featured, setFeatured] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [featuredError, setFeaturedError] = useState(false)
  const [featuredRetry, setFeaturedRetry] = useState(0)
  const [destination, setDestination] = useState('')
  const [checkIn, setCheckIn] = useState('')
  const [checkOut, setCheckOut] = useState('')
  const [guests, setGuests] = useState(2)
  const [searchError, setSearchError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadFeatured() {
      setLoading(true)
      setFeaturedError(false)
      try {
        const data = await api.getFeaturedProperties()
        if (!cancelled) setFeatured(data)
      } catch (error) {
        console.error('Failed to load featured properties:', error)
        if (!cancelled) setFeaturedError(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadFeatured()
    return () => { cancelled = true }
  }, [featuredRetry])

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSearchError('')

    if (checkIn && checkOut && checkOut <= checkIn) {
      setSearchError('Check-out must be after check-in.')
      return
    }

    const params = new URLSearchParams()
    if (destination.trim()) params.set('destination', destination.trim())
    if (checkIn) params.set('check_in', checkIn)
    if (checkOut) params.set('check_out', checkOut)
    params.set('guests', String(Math.max(1, guests)))
    router.push(`/search?${params.toString()}`)
  }

  return (
    <>
      {/* Hero Section */}
      <section className="bg-gradient-to-r from-primary to-secondary text-white py-16">
        <div className="container">
          <h1 className="text-4xl sm:text-5xl font-bold mb-4">Welcome to SL Booking</h1>
          <p className="text-lg sm:text-xl mb-8">Discover the best accommodations across Sri Lanka</p>

          {/* Search Bar */}
          <form onSubmit={handleSearch} className="bg-white text-gray-900 rounded-lg p-4 sm:p-6 shadow-lg">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex items-center gap-2 rounded-lg border border-gray-200 px-3">
                <MapPin className="w-5 h-5 text-gray-500" />
                <input
                  type="text"
                  aria-label="Destination"
                  placeholder="Destination"
                  value={destination}
                  onChange={(event) => setDestination(event.target.value)}
                  className="min-w-0 flex-1 border-0 focus:ring-0 px-0"
                />
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-gray-200 px-3">
                <Calendar className="w-5 h-5 text-gray-500" />
                <input
                  type="date"
                  aria-label="Check-in"
                  value={checkIn}
                  onChange={(event) => setCheckIn(event.target.value)}
                  className="min-w-0 flex-1 border-0 focus:ring-0 px-0"
                />
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-gray-200 px-3">
                <Calendar className="w-5 h-5 text-gray-500" />
                <input
                  type="date"
                  aria-label="Check-out"
                  min={checkIn || undefined}
                  value={checkOut}
                  onChange={(event) => setCheckOut(event.target.value)}
                  className="min-w-0 flex-1 border-0 focus:ring-0 px-0"
                />
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-gray-200 px-3">
                <Users className="w-5 h-5 text-gray-500" />
                <input
                  type="number"
                  aria-label="Guests"
                  min="1"
                  value={guests}
                  onChange={(event) => setGuests(Number(event.target.value) || 1)}
                  className="min-w-0 flex-1 border-0 focus:ring-0 px-0"
                />
              </div>
            </div>
            {searchError && <p role="alert" className="mt-3 text-sm text-red-700">{searchError}</p>}
            <div className="mt-4">
              <button type="submit" className="w-full btn-primary flex items-center justify-center gap-2">
                <Search className="w-5 h-5" />
                Search Properties
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* Featured Properties */}
      <section className="py-16 container">
        <h2 className="text-3xl font-bold mb-8">Featured Properties</h2>

        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading properties...</p>
          </div>
        ) : featuredError ? (
          <div className="text-center py-12" role="alert">
            <p className="text-gray-700 mb-4">Unable to load featured properties. Please try again.</p>
            <button type="button" onClick={() => setFeaturedRetry((retry) => retry + 1)} className="btn-secondary">
              Try again
            </button>
          </div>
        ) : featured.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {featured.map((property) => (
              <PropertyCard key={property.id} property={property} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-600">No featured properties available</p>
          </div>
        )}

        <div className="text-center mt-12">
          <Link href="/search" className="btn-primary">
            View All Properties
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-gray-50">
        <div className="container">
          <h2 className="text-3xl font-bold mb-12 text-center">Why Choose SL Booking?</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                title: 'Best Prices',
                description: 'Competitive rates and exclusive deals on accommodations',
              },
              {
                title: 'Secure Booking',
                description: 'Safe payment processing and booking confirmation',
              },
              {
                title: '24/7 Support',
                description: 'Round-the-clock customer support for your needs',
              },
            ].map((feature, index) => (
              <div key={index} className="card p-6 text-center">
                <h3 className="text-xl font-bold mb-2">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
