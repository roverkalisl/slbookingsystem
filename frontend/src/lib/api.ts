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

class ApiClient {
  private client: AxiosInstance
  private token: string | null = null

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
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
    first_name: string
    last_name: string
  }): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/auth/register/', data)
    if (response.data.access) {
      this.setToken(response.data.access)
    }
    return response.data
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>('/auth/login/', {
      email,
      password,
    })
    if (response.data.access) {
      this.setToken(response.data.access)
    }
    return response.data
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout/')
    } finally {
      this.setToken(null)
    }
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/auth/me/')
    return response.data
  }

  async updateProfile(data: Partial<User>): Promise<User> {
    const response = await this.client.patch<User>('/auth/update-profile/', data)
    return response.data
  }

  // ===== Properties =====
  async getProperties(filters?: SearchFilters): Promise<PaginatedResponse<Property>> {
    const params = new URLSearchParams()

    if (filters) {
      if (filters.destination) params.append('destination', filters.destination)
      if (filters.min_price) params.append('min_price', String(filters.min_price))
      if (filters.max_price) params.append('max_price', String(filters.max_price))
      if (filters.property_type) params.append('type', filters.property_type)
      if (filters.sort_by) params.append('sort_by', filters.sort_by)
    }

    const response = await this.client.get<PaginatedResponse<Property>>(
      `/properties/?${params.toString()}`
    )
    return response.data
  }

  async getProperty(id: string): Promise<Property> {
    const response = await this.client.get<Property>(`/properties/${id}/`)
    return response.data
  }

  async searchProperties(
    destination: string,
    checkIn: string,
    checkOut: string,
    guests: number
  ): Promise<Property[]> {
    const response = await this.client.get<Property[]>(
      `/properties/search/?destination=${destination}&check_in=${checkIn}&check_out=${checkOut}&guests=${guests}`
    )
    return response.data
  }

  async getFeaturedProperties(): Promise<Property[]> {
    const response = await this.client.get<Property[]>('/properties/featured/')
    return response.data
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
    const response = await this.client.post<Booking>('/bookings/', data)
    return response.data
  }

  async getBookings(): Promise<Booking[]> {
    const response = await this.client.get<Booking[]>('/bookings/')
    return response.data
  }

  async getBooking(id: string): Promise<Booking> {
    const response = await this.client.get<Booking>(`/bookings/${id}/`)
    return response.data
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
    const response = await this.client.post<BookingPrice>('/bookings/calculate-price/', data)
    return response.data
  }

  async checkAvailability(
    roomTypeId: string,
    checkIn: string,
    checkOut: string
  ): Promise<{ available: boolean; available_count: number }> {
    const response = await this.client.get<{ available: boolean; available_count: number }>(
      `/bookings/check-availability/?room_type_id=${roomTypeId}&check_in=${checkIn}&check_out=${checkOut}`
    )
    return response.data
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
