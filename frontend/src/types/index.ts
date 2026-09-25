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
  is_staff?: boolean
  is_superuser?: boolean
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
  short_description?: string
  property_type: PropertyType
  city: string
  district: string
  province: string
  address?: string
  postal_code?: string
  latitude?: number
  longitude?: number
  status: 'draft' | 'pending_approval' | 'approved' | 'rejected' | 'suspended' | 'unpublished'
  rating: number
  review_count: number
  average_rating?: number
  total_reviews?: number
  photos: PropertyPhoto[]
  /** Cloudinary URL of the chosen cover photo (first photo as fallback); null without photos */
  cover_photo_url?: string | null
  price_range_min: number
  price_range_max: number
  amenities: Amenity[]
  owner: User
  created_at: string
  updated_at?: string
  published_at?: string
  submitted_at?: string
  reviewed_at?: string
  reviewed_by?: User
  rejection_reason?: string
  house_rules?: string
  nearby_attractions?: string
  /**
   * 'whole_property' (e.g. Entry Villa): the property itself is booked -
   * room_types then contains only the system-managed "Entire Villa" unit.
   * 'room_types': hotels, resorts, guest houses... (owner-managed rooms).
   */
  booking_mode?: BookingMode
  room_types?: RoomType[]
  bedrooms?: number
  max_guests?: number
  contact?: {
    contact_person_name?: string
    contact_phone?: string
    whatsapp_number?: string
    email?: string
  }
}

export type BookingMode = 'room_types' | 'whole_property'

export interface PropertyType {
  id: string
  name: string
  booking_mode?: BookingMode
}

/** Villa-level details of a whole-property listing (GET/PUT /properties/{id}/villa/) */
export interface VillaDetails {
  configured: boolean
  unit_id: string | null
  max_adults?: number
  max_children?: number
  total_occupancy?: number
  number_of_beds?: number
  bed_configuration?: string
  bathroom_type?: string
  base_price?: string | null
  weekend_price?: string | null
}

export interface VillaDetailsInput {
  max_adults: number
  max_children: number
  total_occupancy: number
  number_of_beds: number
  bed_configuration: string
  bathroom_type: string
  base_price: string
  weekend_price: string | null
}

export interface PropertyPhoto {
  id: string
  url: string
  cloudinary_url?: string
  is_cover?: boolean
  caption?: string
  order: number
}

/** Owner photo management: returned by set-cover and delete-photo */
export interface PropertyPhotoState {
  cover_photo_url: string | null
  photos: Array<{
    id: string
    cloudinary_url: string
    cloudinary_public_id?: string
    is_cover: boolean
    display_order: number
  }>
}

export interface RoomType {
  id: string
  property_id: string
  name: string
  description?: string
  max_adults: number
  max_children: number
  total_occupancy: number
  number_of_beds?: number
  bed_configuration?: string
  bathroom_type?: string
  /** True for the system-managed "Entire Villa" unit of a whole-property listing */
  is_property_unit?: boolean
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
  property_id?: string
  property_name?: string
  room_type_name?: string
  guest_name?: string
  guest_email?: string
  guest_phone?: string
  check_in_date: string
  check_out_date: string
  number_of_nights: number
  number_of_adults: number
  number_of_children: number
  total_price: number
  /** Booking.STATUS_CHOICES (apps/bookings/models.py) */
  status: BookingStatus
  /** Booking.PAYMENT_STATUS_CHOICES - set only by the backend (webhook / owner confirmation) */
  payment_status: BookingPaymentStatus
  special_requests?: string
  created_at: string
  guests?: BookingGuest[]
  /** Property owner's WhatsApp - returned only to this booking's guest (null when not set) */
  owner_whatsapp_number?: string | null
  /** https://wa.me/<number>?text=<booking inquiry> - returned only to this booking's guest */
  owner_whatsapp_url?: string | null
}

export interface BookingGuest {
  id: string
  first_name: string
  last_name: string
  email: string
  is_primary_guest: boolean
}

/**
 * Shape matches PriceBreakdownSerializer (apps/bookings/serializers.py)
 * exactly, as returned by POST /bookings/calculate-price/.
 */
export interface BookingPrice {
  nights: number
  room_price_per_night: number
  room_subtotal: number
  guest_fees: number
  subtotal: number
  discount: number
  service_fee: number
  tax: number
  total: number
  currency: string
}

export type BookingStatus =
  | 'pending' | 'confirmed' | 'payment_pending' | 'paid' | 'completed'
  | 'cancelled' | 'rejected' | 'no_show' | 'refunded' | 'partially_refunded'

export type BookingPaymentStatus =
  | 'pending' | 'processing' | 'paid' | 'failed' | 'cancelled' | 'refunded' | 'partially_refunded'

/** PaymentInitiateSerializer.payment_method choices */
export type PaymentMethod = 'stripe' | 'pay_at_property' | 'bank_transfer'

/** Response data of POST /payments/initiate/ (PaymentService.initiate_payment) */
export interface PaymentInitiation {
  success: boolean
  payment_id: string
  /** Stripe: hosted Checkout URL to redirect to. Offline methods: null. */
  payment_url: string | null
  payment_method: PaymentMethod
  /** Informational only - the server-side booking total that will be charged */
  amount: number | string
  currency: string
}

export interface Payment {
  id: string
  booking_id: string
  amount: number
  currency: string
  payment_method: PaymentMethod
  status: 'pending' | 'completed' | 'failed' | 'refunded'
  processor_reference?: string
  created_at: string
}

/** Matches NotificationSerializer exactly. status: 'read' means read - any
 * other value ('pending'/'sent'/'failed') means unread; there is no
 * separate unread/archived status on the backend. */
export interface Notification {
  id: string
  notification_type: string
  title: string
  message: string
  channel: 'email' | 'sms' | 'push' | 'in_app'
  status: 'pending' | 'sent' | 'failed' | 'read'
  related_booking?: string
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
