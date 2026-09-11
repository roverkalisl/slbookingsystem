/**
 * Property card component for listing
 */

'use client'

import Link from 'next/link'
import Image from 'next/image'
import { Star, MapPin } from 'lucide-react'
import type { Property } from '@/types'

interface PropertyCardProps {
  property: Property
}

export function PropertyCard({ property }: PropertyCardProps) {
  const imageUrl =
    property.photos.length > 0
      ? property.photos[0].url
      : 'https://via.placeholder.com/300x200?text=No+Image'

  return (
    <Link href={`/property/${property.id}`}>
      <div className="bg-white rounded-lg shadow hover:shadow-lg transition cursor-pointer overflow-hidden">
        {/* Image */}
        <div className="relative h-48 w-full bg-gray-200">
          <Image
            src={imageUrl}
            alt={property.name}
            fill
            className="object-cover"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        </div>

        {/* Content */}
        <div className="p-4">
          {/* Name */}
          <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">{property.name}</h3>

          {/* Location */}
          <div className="flex items-center gap-1 text-gray-600 text-sm mt-2">
            <MapPin className="w-4 h-4" />
            <span>
              {property.city}, {property.district}
            </span>
          </div>

          {/* Rating */}
          <div className="flex items-center gap-2 mt-3">
            <div className="flex items-center gap-1">
              <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
              <span className="text-sm font-semibold">{property.rating.toFixed(1)}</span>
            </div>
            <span className="text-sm text-gray-500">({property.review_count} reviews)</span>
          </div>

          {/* Price */}
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">Starting from</p>
            <p className="text-2xl font-bold text-primary">
              LKR {property.price_range_min.toLocaleString()}
            </p>
            <p className="text-xs text-gray-500">per night</p>
          </div>
        </div>
      </div>
    </Link>
  )
}
