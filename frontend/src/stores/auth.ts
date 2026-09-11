/**
 * Authentication store using Zustand
 */

import { create } from 'zustand'
import { api } from '@/lib/api'
import type { User } from '@/types'

interface AuthStore {
  user: User | null
  isLoading: boolean
  error: string | null
  isAuthenticated: boolean

  // Actions
  login: (email: string, password: string) => Promise<void>
  register: (data: {
    email: string
    password: string
    first_name: string
    last_name: string
    role: string
  }) => Promise<void>
  logout: () => Promise<void>
  fetchUser: () => Promise<void>
  clearError: () => void
}

export const useAuth = create<AuthStore>((set) => ({
  user: null,
  isLoading: false,
  error: null,
  isAuthenticated: false,

  login: async (email: string, password: string) => {
    try {
      set({ isLoading: true, error: null })
      const response = await api.login(email, password)
      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch (error: any) {
      let errorMessage = 'Login failed'

      // Handle different error response formats
      if (error.response?.data) {
        const data = error.response.data
        if (typeof data === 'object') {
          // Check for specific field errors
          const firstError = Object.values(data)[0]
          if (Array.isArray(firstError) && firstError[0]) {
            errorMessage = String(firstError[0])
          } else if (data.detail) {
            errorMessage = data.detail
          } else if (data.message) {
            errorMessage = data.message
          } else if (typeof data === 'string') {
            errorMessage = data
          }
        }
      } else if (error.message) {
        errorMessage = error.message
      }

      set({
        error: errorMessage,
        isLoading: false,
      })
      throw error
    }
  },

  register: async (data) => {
    try {
      set({ isLoading: true, error: null })
      const response = await api.register(data)
      set({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch (error: any) {
      let errorMessage = 'Registration failed'

      // Handle different error response formats
      if (error.response?.data) {
        const data = error.response.data
        if (typeof data === 'object') {
          // Check for specific field errors
          const firstError = Object.values(data)[0]
          if (Array.isArray(firstError) && firstError[0]) {
            errorMessage = String(firstError[0])
          } else if (data.detail) {
            errorMessage = data.detail
          } else if (data.message) {
            errorMessage = data.message
          } else if (typeof data === 'string') {
            errorMessage = data
          }
        }
      } else if (error.message) {
        errorMessage = error.message
      }

      set({
        error: errorMessage,
        isLoading: false,
      })
      throw error
    }
  },

  logout: async () => {
    try {
      set({ isLoading: true })
      await api.logout()
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      })
    } catch (error) {
      set({ isLoading: false })
    }
  },

  fetchUser: async () => {
    try {
      set({ isLoading: true })
      const user = await api.getCurrentUser()
      set({
        user,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch (error) {
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      })
    }
  },

  clearError: () => set({ error: null }),
}))
