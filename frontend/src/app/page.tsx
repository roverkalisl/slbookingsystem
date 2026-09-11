/**
 * Home page - Hero + Featured Properties
 */

'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { PropertyCard } from '@/components/PropertyCard'
import { api } from '@/lib/api'
import type { Property } from '@/types'
import { Search, MapPin, Calendar, Users } from 'lucide-react'

export default function Home() {
  const [featured, setFeatured] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadFeatured() {
      try {
        const data = await api.getFeaturedProperties()
        setFeatured(data)
      } catch (error) {
        console.error('Failed to load featured properties:', error)
      } finally {
        setLoading(false)
      }
    }

    loadFeatured()
  }, [])

  return (
    <>
      {/* Hero Section */}
      <section className="bg-gradient-to-r from-primary to-secondary text-white py-16">
        <div className="container">
          <h1 className="text-5xl font-bold mb-4">Welcome to SL Booking</h1>
          <p className="text-xl mb-8">Discover the best accommodations across Sri Lanka</p>

          {/* Search Bar */}
          <div className="bg-white text-gray-900 rounded-lg p-6 shadow-lg">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-gray-500" />
                <input
                  type="text"
                  placeholder="Destination"
                  className="flex-1 border-0 focus:ring-0 px-0"
                />
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="w-5 h-5 text-gray-500" />
                <input
                  type="date"
                  className="flex-1 border-0 focus:ring-0 px-0"
                />
              </div>
              <div className="flex items-center gap-2">
                <Calendar className="w-5 h-5 text-gray-500" />
                <input
                  type="date"
                  className="flex-1 border-0 focus:ring-0 px-0"
                />
              </div>
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-gray-500" />
                <input
                  type="number"
                  min="1"
                  defaultValue="2"
                  className="flex-1 border-0 focus:ring-0 px-0"
                />
              </div>
            </div>
            <div className="mt-4">
              <Link
                href="/search"
                className="w-full btn-primary flex items-center justify-center gap-2"
              >
                <Search className="w-5 h-5" />
                Search Properties
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Properties */}
      <section className="py-16 container">
        <h2 className="text-3xl font-bold mb-8">Featured Properties</h2>

        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading properties...</p>
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
