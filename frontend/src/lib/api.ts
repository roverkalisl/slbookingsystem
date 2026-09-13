/**
 * API client for SL Booking backend
 * Handles authentication, requests, and error handling
 */

import axios, { AxiosInstance, AxiosError } from 'axios'
import type {
  Property,
  Booking,
  BookingPrice,
  User,
  AuthResponse,
  PaginatedResponse,
  SearchFilters,
  Notification,
  Review,
} from '@/types'

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'https://slbookingsystem.onrender.com/api'

class ApiClient {
  private client: AxiosInstance
  private token: string | null = null

  private normalizeProperty(raw: any): Property {
    const photos = raw.photos || (raw.cover_photo_url ? [{ id: raw.id, url: raw.cover_photo_url }] : [])
    return {
      ...raw,
      property_type: raw.property_type || {
        id: raw.property_type_id || '',
        name: raw.property_type_name || '',
      },
      rating: Number(raw.rating ?? raw.average_rating ?? 0),
      review_count: Number(raw.review_count ?? raw.total_reviews ?? 0),
      price_range_min: Number(raw.price_range_min ?? raw.min_price ?? 0),
      price_range_max: Number(raw.price_range_max ?? raw.min_price ?? 0),
      photos: photos.map((photo: any) => ({
        ...photo,
        url: photo.url || photo.cloudinary_url,
      })),
      amenities: raw.amenities || [],
      room_types: raw.room_types || [],
    }
  }

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add token to requests
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`
      }
      return config
    })

    // Handle errors
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Unauthorized - clear token and redirect to login
          this.setToken(null)
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )

    // Load token from localStorage
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('access_token')
      if (stored) {
        this.token = stored
      }
    }
  }

  setToken(token: string | null) {
    this.token = token
    if (token) {
      localStorage.setItem('access_token', token)
    } else {
      localStorage.removeItem('access_token')
    }
  }

  // ===== Authentication =====
  async register(data: {
    email: string
    password: string
    password2?: string
    first_name: string
    last_name: string
    role: string
  }): Promise<AuthResponse> {
    const response = await this.client.post<any>('/auth/register/', {
      ...data,
      password2: data.password2 || data.password, // Default to password if password2 not provided
    })
    const authData = response.data.data || response.data
    if (authData.access) {
      this.setToken(authData.access)
    }
    return authData
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await this.client.post<any>('/auth/login/', {
      email,
      password,
    })
    const authData = response.data.data || response.data
    if (authData.access) {
      this.setToken(authData.access)
    }
    return authData
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout/')
    } finally {
      this.setToken(null)
    }
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<any>('/auth/me/')
    return response.data.data || response.data
  }

  async updateProfile(data: Partial<User>): Promise<User> {
    const response = await this.client.patch<User>('/auth/update-profile/', data)
    return response.data
  }

  // ===== Properties =====
  async getProperties(filters?: SearchFilters): Promise<PaginatedResponse<Property>> {
    const params = new URLSearchParams()

    if (filters) {
      if (filters.destination) params.append('city', filters.destination)
      if (filters.min_price) params.append('min_price', String(filters.min_price))
      if (filters.max_price) params.append('max_price', String(filters.max_price))
      if (filters.property_type) params.append('property_types', filters.property_type)
      if (filters.check_in) params.append('check_in', filters.check_in)
      if (filters.check_out) params.append('check_out', filters.check_out)
      if (filters.guests) params.append('adults', String(filters.guests))
      if (filters.sort_by) {
        params.append('sort_by', filters.sort_by === 'price_asc' || filters.sort_by === 'price_desc' ? 'price' : filters.sort_by)
        if (filters.sort_by === 'price_asc' || filters.sort_by === 'price_desc') {
          params.append('sort_direction', filters.sort_by === 'price_asc' ? 'asc' : 'desc')
        }
      }
    }

    const response = await this.client.get<PaginatedResponse<any>>(
      `/properties/search/advanced/?${params.toString()}`
    )
    return {
      ...response.data,
      results: (response.data.results || []).map((property) => this.normalizeProperty(property)),
    }
  }

  async getProperty(id: string): Promise<Property> {
    const response = await this.client.get<any>(`/properties/${id}/`)
    return this.normalizeProperty(response.data.data || response.data)
  }

  async searchProperties(
    destination: string,
    checkIn: string,
    checkOut: string,
    guests: number
  ): Promise<Property[]> {
    const response = await this.client.get<any>(
      `/properties/search/advanced/?city=${encodeURIComponent(destination)}&check_in=${checkIn}&check_out=${checkOut}&adults=${guests}`
    )
    return (response.data.results || response.data.data || []).map((property: any) =>
      this.normalizeProperty(property)
    )
  }

  async getFeaturedProperties(): Promise<Property[]> {
    const response = await this.client.get<any>('/properties/search/featured/')
    return (response.data.data || response.data).map((property: any) =>
      this.normalizeProperty(property)
    )
  }

  // ===== Bookings =====
  async createBooking(data: {
      room_type_id: string
    check_in: string
    check_out: string
    num_adults: number
    num_children: number
    special_requests?: string
  }): Promise<Booking> {
    const response = await this.client.post<any>('/bookings/', {
      room_type_id: data.room_type_id,
      check_in_date: data.check_in,
      check_out_date: data.check_out,
      number_of_adults: data.num_adults,
      number_of_children: data.num_children,
      special_requests: data.special_requests,
    })
    return response.data.data || response.data
  }

  async getBookings(): Promise<Booking[]> {
    const response = await this.client.get<any>('/bookings/')
    return response.data.results || response.data.data || response.data
  }

  async getBooking(id: string): Promise<Booking> {
    const response = await this.client.get<any>(`/bookings/${id}/`)
    return response.data.data || response.data
  }

  async cancelBooking(id: string): Promise<void> {
    await this.client.post(`/bookings/${id}/cancel/`)
  }

  async calculatePrice(data: {
    room_type_id: string
    check_in: string
    check_out: string
    num_adults: number
    num_children?: number
  }): Promise<BookingPrice> {
    const response = await this.client.post<any>('/bookings/calculate-price/', {
      room_type_id: data.room_type_id,
      check_in_date: data.check_in,
      check_out_date: data.check_out,
      number_of_adults: data.num_adults,
      number_of_children: data.num_children || 0,
    })
    return response.data.data || response.data
  }

  async checkAvailability(
    roomTypeId: string,
    checkIn: string,
    checkOut: string
  ): Promise<{ available: boolean; available_count: number }> {
    const response = await this.client.post<any>('/bookings/check-availability/', {
      room_type_id: roomTypeId,
      check_in_date: checkIn,
      check_out_date: checkOut,
    })
    const data = response.data.data || response.data
    return {
      available: data.is_available,
      available_count: data.available_count,
    }
  }

  // ===== Payments =====
  async initiatePayment(data: {
    booking_id: string
    amount: number
    method: 'stripe' | 'pay_at_property' | 'bank_transfer'
  }) {
    const response = await this.client.post('/payments/initiate/', data)
    return response.data
  }

  async confirmPayment(paymentId: string) {
    const response = await this.client.post(`/payments/${paymentId}/confirm/`)
    return response.data
  }

  async processRefund(paymentId: string, amount: number, reason: string) {
    const response = await this.client.post(`/payments/${paymentId}/refund/`, {
      amount,
      reason,
    })
    return response.data
  }

  // ===== Notifications =====
  async getNotifications(): Promise<Notification[]> {
    const response = await this.client.get<Notification[]>('/notifications/')
    return response.data
  }

  async markNotificationAsRead(id: string): Promise<void> {
    await this.client.post(`/notifications/${id}/mark-as-read/`)
  }

  async markAllNotificationsAsRead(): Promise<void> {
    await this.client.post('/notifications/mark-all-as-read/')
  }

  // ===== Reviews =====
  async submitReview(data: {
    booking_id: string
    rating: number
    title: string
    comment: string
  }): Promise<Review> {
    const response = await this.client.post<Review>('/reviews/', data)
    return response.data
  }

  async getReviews(propertyId: string): Promise<Review[]> {
    const response = await this.client.get<Review[]>(`/reviews/?property_id=${propertyId}`)
    return response.data
  }
}

export const api = new ApiClient()
