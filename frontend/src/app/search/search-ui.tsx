/**
 * Search results page with filters and sorting
 */

'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { PropertyCard } from '@/components/PropertyCard'
import { api } from '@/lib/api'
import { trackEvent } from '@/lib/analytics'
import type { Property, SearchFilters } from '@/types'
import { Filter, ChevronDown, MapPin, Calendar, Users } from 'lucide-react'

function SearchContent() {
  const searchParams = useSearchParams()
  const [properties, setProperties] = useState<Property[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const [retry, setRetry] = useState(0)
  const [showFilters, setShowFilters] = useState(false)
  const [sortBy, setSortBy] = useState<'price_asc' | 'price_desc' | 'rating' | 'newest'>('price_asc')
  const [priceRange, setPriceRange] = useState({ min: 0, max: 100000 })

  // Get search params
  const destination = searchParams.get('destination') || ''
  const checkIn = searchParams.get('check_in') || ''
  const checkOut = searchParams.get('check_out') || ''
  const guests = Math.max(1, parseInt(searchParams.get('guests') || '2', 10) || 2)
  const propertyType = searchParams.get('property_type') || ''

  // One analytics event per distinct search (not on sort/price-slider changes).
  // Dates are not sent; only destination, property type and guest count.
  useEffect(() => {
    trackEvent('property_search', {
      destination: destination || undefined,
      property_type: propertyType || undefined,
      guest_count: Number.isFinite(guests) ? guests : undefined,
    })
  }, [destination, propertyType, guests])

  useEffect(() => {
    let cancelled = false

    async function loadProperties() {
      setLoading(true)
      setLoadError(false)
      setProperties([])
      try {
        const filters: SearchFilters = {
          destination: destination || undefined,
          check_in: checkIn || undefined,
          check_out: checkOut || undefined,
          sort_by: sortBy,
          min_price: priceRange.min,
          max_price: priceRange.max,
          guests,
        }

        const response = await api.getProperties(filters)
        if (!cancelled) setProperties(response.results || [])
      } catch (error) {
        console.error('Failed to load properties:', error)
        if (!cancelled) setLoadError(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadProperties()
    return () => { cancelled = true }
  }, [destination, checkIn, checkOut, guests, sortBy, priceRange, retry])

  const filteredByPrice = properties.filter(
    (p) => p.price_range_min >= priceRange.min && p.price_range_max <= priceRange.max
  )

  return (
    <>
      {/* Header */}
      <div className="bg-white border-b border-gray-200 py-6 mb-6">
        <div className="container">
          <h1 className="text-3xl font-bold mb-4">Search Results</h1>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm text-gray-600">
            {destination && (
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4" />
                <span>{destination}</span>
              </div>
            )}
            {checkIn && (
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                <span>{checkIn} to {checkOut}</span>
              </div>
            )}
            {guests && (
              <div className="flex items-center gap-2">
                <Users className="w-4 h-4" />
                <span>{guests} guests</span>
              </div>
            )}
            <div className="text-gray-700 font-semibold">
              {filteredByPrice.length} properties found
            </div>
          </div>
        </div>
      </div>

      <div className="container mb-12">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar Filters */}
          <div className="lg:col-span-1">
            <button
              type="button"
              aria-expanded={showFilters}
              aria-controls="search-filters"
              onClick={() => setShowFilters(!showFilters)}
              className="w-full lg:hidden mb-4 flex items-center justify-between px-4 py-3 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <span className="flex items-center gap-2">
                <Filter className="w-5 h-5" />
                Filters
              </span>
              <ChevronDown className={`w-5 h-5 transition ${showFilters ? 'rotate-180' : ''}`} />
            </button>

            <div id="search-filters" className={`${showFilters ? 'block' : 'hidden'} lg:block space-y-6 bg-white p-6 rounded-lg`}>
              {/* Price Range Filter */}
              <div>
                <h3 className="font-semibold mb-4">Price Range</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm text-gray-600">Min Price</label>
                    <input
                      type="number"
                      value={priceRange.min}
                      onChange={(e) =>
                        setPriceRange({ ...priceRange, min: parseInt(e.target.value) || 0 })
                      }
                      className="w-full border border-gray-300 rounded px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="text-sm text-gray-600">Max Price</label>
                    <input
                      type="number"
                      value={priceRange.max}
                      onChange={(e) =>
                        setPriceRange({ ...priceRange, max: parseInt(e.target.value) || 100000 })
                      }
                      className="w-full border border-gray-300 rounded px-3 py-2"
                    />
                  </div>
                </div>
              </div>

              {/* Sort Options */}
              <div>
                <h3 className="font-semibold mb-4">Sort By</h3>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="w-full border border-gray-300 rounded px-3 py-2"
                >
                  <option value="price_asc">Price: Low to High</option>
                  <option value="price_desc">Price: High to Low</option>
                  <option value="rating">Top Rated</option>
                  <option value="newest">Newest First</option>
                </select>
              </div>

              {/* Clear Filters */}
              <button
                onClick={() => {
                  setPriceRange({ min: 0, max: 100000 })
                  setSortBy('price_asc')
                }}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
              >
                Clear Filters
              </button>
            </div>
          </div>

          {/* Results Grid */}
          <div className="lg:col-span-3">
            {loading ? (
              <div className="text-center py-12">
                <p className="text-gray-600">Loading properties...</p>
              </div>
            ) : loadError ? (
              <div className="text-center py-12 bg-white rounded-lg" role="alert">
                <p className="text-gray-700 mb-4">Unable to load properties. Please try again.</p>
                <button type="button" onClick={() => setRetry((value) => value + 1)} className="btn-secondary">
                  Try again
                </button>
              </div>
            ) : filteredByPrice.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {filteredByPrice.map((property) => (
                  <PropertyCard key={property.id} property={property} />
                ))}
              </div>
            ) : (
              <div className="text-center py-12 bg-white rounded-lg">
                <p className="text-gray-600 mb-4">No properties found matching your criteria</p>
                <Link href="/" className="btn-primary">
                  Browse All Properties
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="text-center py-12">Loading...</div>}>
      <SearchContent />
    </Suspense>
  )
}
