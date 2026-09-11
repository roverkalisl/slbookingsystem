/**
 * Core TypeScript types for SL Booking frontend
 */

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  phone?: string
  avatar_url?: string
  bio?: string
  email_verified?: boolean
  phone_verified?: boolean
  preferred_language?: string
  notification_email?: boolean
  notification_sms?: boolean
  roles?: string[]
  created_at: string
  updated_at?: string
}

export interface AuthResponse {
  access: string
  refresh: string
  user: User
}

export interface Property {
  id: string
  name: string
  description: string
  property_type: PropertyType
  city: string
  district: string
  province: string
  status: 'draft' | 'pending_approval' | 'approved' | 'published' | 'suspended'
  rating: number
  review_count: number
  photos: PropertyPhoto[]
  price_range_min: number
  price_range_max: number
  amenities: Amenity[]
  owner: User
  created_at: string
}

export interface PropertyType {
  id: string
  name: string
}

export interface PropertyPhoto {
  id: string
  url: string
  caption?: string
  order: number
}

export interface RoomType {
  id: string
  property_id: string
  name: string
  description?: string
  max_adults: number
  max_children: number
  total_occupancy: number
  photos: PropertyPhoto[]
  amenities: Amenity[]
  pricing: Pricing
}

export interface Pricing {
  id: string
  room_type_id: string
  base_price: number
  weekend_price: number
  extra_guest_fee: number
  currency: string
}

export interface Amenity {
  id: string
  name: string
  icon?: string
}

export interface Booking {
  id: string
  booking_reference: string
  room_type_id: string
  check_in_date: string
  check_out_date: string
  number_of_nights: number
  number_of_adults: number
  number_of_children: number
  total_price: number
  status: 'pending' | 'confirmed' | 'paid' | 'completed' | 'cancelled'
  payment_status: 'pending' | 'processing' | 'paid' | 'failed'
  special_requests?: string
  created_at: string
  guests: BookingGuest[]
}

export interface BookingGuest {
  id: string
  first_name: string
  last_name: string
  email: string
  is_primary_guest: boolean
}

export interface BookingPrice {
  base_price: number
  guest_fees: number
  discount: number
  tax: number
  total_price: number
  breakdown: {
    base_total: number
    service_fee: number
    tax_amount: number
  }
}

export interface Payment {
  id: string
  booking_id: string
  amount: number
  currency: string
  payment_method: 'stripe' | 'pay_at_property' | 'bank_transfer'
  status: 'pending' | 'completed' | 'failed' | 'refunded'
  processor_reference?: string
  created_at: string
}

export interface Notification {
  id: string
  notification_type: string
  title: string
  message: string
  channel: 'email' | 'sms' | 'push' | 'in_app'
  status: 'unread' | 'read' | 'archived'
  related_booking_id?: string
  created_at: string
}

export interface Review {
  id: string
  booking_id: string
  rating: number
  title: string
  comment: string
  guest: User
  property: Property
  created_at: string
}

export interface SearchFilters {
  destination?: string
  check_in?: string
  check_out?: string
  min_price?: number
  max_price?: number
  property_type?: string
  amenities?: string[]
  guests?: number
  rooms?: number
  sort_by?: 'price_asc' | 'price_desc' | 'rating' | 'newest'
}

export interface PaginatedResponse<T> {
  count: number
  next?: string
  previous?: string
  results: T[]
}
