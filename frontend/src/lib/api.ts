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
    console.log('[API CLIENT] ApiClient constructor called')
    console.log('[API CLIENT] API_BASE_URL:', API_BASE_URL)
    try {
      this.client = axios.create({
        baseURL: API_BASE_URL,
        headers: {
          'Content-Type': 'application/json',
        },
      })
      console.log('[API CLIENT] Axios instance created successfully')

      // Add token to requests
      this.client.interceptors.request.use((config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`
        }
        console.log('[API CLIENT INTERCEPTOR] Request:', {
          method: config.method?.toUpperCase(),
          url: config.url,
          hasAuth: !!config.headers.Authorization,
        })
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
      console.log('[API CLIENT] Interceptors configured')

      // Load token from localStorage
      if (typeof window !== 'undefined') {
        const stored = localStorage.getItem('access_token')
        if (stored) {
          this.token = stored
          console.log('[API CLIENT] Loaded existing token from localStorage')
        }
      }
      console.log('[API CLIENT] Constructor completed successfully')
    } catch (error) {
      console.error('[API CLIENT] Constructor failed:', error instanceof Error ? error.message : String(error))
      throw error
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
    console.log('[API CLIENT] login() called - email exists:', !!email, 'password exists:', !!password)
    console.log('[API CLIENT] API_BASE_URL:', API_BASE_URL)
    console.log('[API CLIENT] Full URL will be:', API_BASE_URL + '/auth/login/')
    try {
      console.log('[API CLIENT] Calling axios.post() to /auth/login/...')
      const response = await this.client.post<any>('/auth/login/', {
        email,
        password,
      })
      console.log('[API CLIENT] axios.post() succeeded - HTTP Status:', response.status)
      console.log('[API CLIENT] Response data keys:', Object.keys(response.data || {}))
      const authData = response.data.data || response.data
      console.log('[API CLIENT] authData keys:', Object.keys(authData || {}))
      console.log('[API CLIENT] authData has access token:', !!authData?.access)
      if (authData.access) {
        this.setToken(authData.access)
        console.log('[API CLIENT] Access token stored in localStorage')
      }
      return authData
    } catch (error: any) {
      console.log('[API CLIENT] axios.post() threw error')
      if (error.response) {
        console.log('[API CLIENT] HTTP Status:', error.response.status)
        console.log('[API CLIENT] Response data keys:', Object.keys(error.response.data || {}))
      } else if (error.request) {
        console.log('[API CLIENT] No response received - request made but no response')
        console.log('[API CLIENT] Request URL:', error.request.responseURL)
      } else {
        console.log('[API CLIENT] Error message:', error.message)
      }
      throw error
    }
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

  async createProperty(data: any): Promise<Property> {
    const response = await this.client.post<any>('/properties/', data)
    const responseData = response.data.data || response.data
    console.log('[API CLIENT] createProperty response:', {
      status: response.status,
      hasData: !!responseData,
      hasId: !!responseData?.id,
      idValue: responseData?.id ? responseData.id.substring(0, 8) + '...' : 'null',
      responseStructure: Object.keys(responseData || {}).slice(0, 5),
    })
    return this.normalizeProperty(responseData)
  }

  async updateProperty(id: string, data: any): Promise<Property> {
    console.log('[API CLIENT] updateProperty called with ID:', id.substring(0, 8) + '...')
    const response = await this.client.put<any>(`/properties/${id}/`, data)
    const responseData = response.data.data || response.data
    console.log('[API CLIENT] updateProperty response:', {
      status: response.status,
      hasData: !!responseData,
    })
    return this.normalizeProperty(responseData)
  }

  async deleteProperty(id: string): Promise<void> {
    await this.client.delete(`/properties/${id}/`)
  }

  async submitPropertyForApproval(id: string): Promise<Property> {
    const response = await this.client.post<any>(`/properties/${id}/submit-for-approval/`)
    return this.normalizeProperty(response.data.data || response.data)
  }

  async approveProperty(id: string): Promise<Property> {
    const response = await this.client.post<any>(`/properties/${id}/approve/`)
    return this.normalizeProperty(response.data.data || response.data)
  }

  async rejectProperty(id: string, reason: string): Promise<Property> {
    const response = await this.client.post<any>(`/properties/${id}/reject/`, {
      rejection_reason: reason,
    })
    return this.normalizeProperty(response.data.data || response.data)
  }

  async unsuspendProperty(id: string): Promise<Property> {
    const response = await this.client.post<any>(`/properties/${id}/unsuspend/`)
    return this.normalizeProperty(response.data.data || response.data)
  }

  async unpublishProperty(id: string): Promise<Property> {
    const response = await this.client.post<any>(`/properties/${id}/unpublish/`)
    return this.normalizeProperty(response.data.data || response.data)
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

  // ===== Admin: Users =====
  async getAdminUsers(
    search?: string,
    role?: string,
    is_active?: boolean,
    page: number = 1,
    page_size: number = 20
  ): Promise<PaginatedResponse<User>> {
    const params = new URLSearchParams()
    if (search) params.append('search', search)
    if (role) params.append('roles__name', role)
    if (is_active !== undefined) params.append('is_active', String(is_active))
    params.append('page', String(page))
    params.append('page_size', String(page_size))

    const response = await this.client.get<any>(
      `/admin/users/?${params.toString()}`
    )
    return {
      ...response.data,
      results: response.data.results || [],
    }
  }

  async getAdminUserDetail(id: string): Promise<User> {
    const response = await this.client.get<any>(`/admin/users/${id}/`)
    return response.data.data || response.data
  }

  async activateUser(id: string): Promise<User> {
    const response = await this.client.post<any>(`/admin/users/${id}/activate/`, {})
    return response.data.data || response.data
  }

  async deactivateUser(id: string, reason?: string): Promise<User> {
    const response = await this.client.post<any>(`/admin/users/${id}/deactivate/`, {
      reason: reason || '',
    })
    return response.data.data || response.data
  }

  // ===== Admin: Dashboard Stats =====
  async getAdminDashboardStats(): Promise<any> {
    const response = await this.client.get<any>('/admin/stats/dashboard/')
    return response.data.data || response.data
  }

  // ===== Admin: Bookings =====
  async getAdminBookings(
    status?: string,
    payment_status?: string,
    search?: string,
    page: number = 1,
    page_size: number = 20
  ): Promise<PaginatedResponse<any>> {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    if (payment_status) params.append('payment_status', payment_status)
    if (search) params.append('search', search)
    params.append('page', String(page))
    params.append('page_size', String(page_size))

    const response = await this.client.get<any>(
      `/bookings/?${params.toString()}`
    )
    return {
      ...response.data,
      results: response.data.results || [],
    }
  }

  async getAdminBookingDetail(id: string): Promise<any> {
    const response = await this.client.get<any>(`/admin/bookings/${id}/`)
    return response.data.data || response.data
  }

  async updateAdminBookingStatus(id: string, status: string): Promise<any> {
    const response = await this.client.patch<any>(`/admin/bookings/${id}/status/`, {
      status,
    })
    return response.data.data || response.data
  }

  async cancelAdminBooking(id: string, reason?: string): Promise<any> {
    const response = await this.client.post<any>(`/admin/bookings/${id}/cancel/`, {
      reason: reason || 'admin_request',
    })
    return response.data.data || response.data
  }

  // ===== Admin: Payments =====
  async getAdminPayments(
    status?: string,
    payment_method?: string,
    search?: string,
    page: number = 1,
    page_size: number = 20
  ): Promise<PaginatedResponse<any>> {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    if (payment_method) params.append('payment_method', payment_method)
    if (search) params.append('search', search)
    params.append('page', String(page))
    params.append('page_size', String(page_size))

    const response = await this.client.get<any>(
      `/admin/payments/?${params.toString()}`
    )
    return {
      ...response.data,
      results: response.data.results || [],
    }
  }

  async getAdminPaymentDetail(id: string): Promise<any> {
    const response = await this.client.get<any>(`/admin/payments/${id}/`)
    return response.data.data || response.data
  }

  async requestAdminRefund(id: string, amount?: number, reason?: string): Promise<any> {
    const response = await this.client.post<any>(`/admin/payments/${id}/request-refund/`, {
      amount,
      reason,
    })
    return response.data.data || response.data
  }

  async getAdminRefunds(
    status?: string,
    page: number = 1,
    page_size: number = 20
  ): Promise<PaginatedResponse<any>> {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    params.append('page', String(page))
    params.append('page_size', String(page_size))

    const response = await this.client.get<any>(
      `/admin/refunds/?${params.toString()}`
    )
    return {
      ...response.data,
      results: response.data.results || [],
    }
  }
}

export const api = new ApiClient()
