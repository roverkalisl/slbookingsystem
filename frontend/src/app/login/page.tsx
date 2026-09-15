/**
 * Login page
 */

'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/stores/auth'
import { useForm } from 'react-hook-form'
import { Home } from 'lucide-react'

interface LoginForm {
  email: string
  password: string
}

export default function LoginPage() {
  const router = useRouter()
  const { isAuthenticated, login, error, clearError } = useAuth()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>()

  // DIAGNOSTIC: Log when component mounts
  useEffect(() => {
    console.log('[LOGIN PAGE] Mounted - diagnostic logging enabled')
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      console.log('[LOGIN PAGE] isAuthenticated=true, redirecting to /bookings')
      router.push('/bookings')
    }
  }, [isAuthenticated, router])

  const onSubmit = async (data: LoginForm) => {
    console.log('[LOGIN PAGE] onSubmit entered - form data exists')
    console.log('[LOGIN PAGE] Email field exists:', !!data.email)
    console.log('[LOGIN PAGE] Password field exists:', !!data.password)

    try {
      console.log('[LOGIN PAGE] Calling auth.login()...')
      await login(data.email, data.password)
      console.log('[LOGIN PAGE] login() succeeded, attempting redirect to /bookings')
      router.push('/bookings')
    } catch (err) {
      console.log('[LOGIN PAGE] login() threw error:', err instanceof Error ? err.message : String(err))
      // Error is stored in auth store
    }
  }

  // DIAGNOSTIC: Handle form validation failures
  const onInvalid = (errors: any) => {
    console.log('[LOGIN PAGE] Form validation FAILED - invalid fields:', Object.keys(errors))
    Object.entries(errors).forEach(([field, error]: [string, any]) => {
      console.log(`  - ${field}: ${error.message}`)
    })
  }

  // DIAGNOSTIC: Log button click
  const handleSignInClick = () => {
    console.log('[LOGIN PAGE] Sign In button clicked')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary to-secondary flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="flex items-center justify-center gap-2 mb-4">
            <div className="bg-white p-2 rounded-lg">
              <Home className="w-6 h-6 text-primary" />
            </div>
            <span className="text-2xl font-bold text-white">SL Booking</span>
          </Link>
          <p className="text-white/80">Welcome back! Sign in to your account</p>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-lg shadow-xl p-8">
          {error && (
            <div className="mb-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
              {error}
              <button
                onClick={clearError}
                className="ml-2 text-red-600 hover:text-red-800 font-semibold"
              >
                Dismiss
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit, onInvalid)} className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-sm font-semibold mb-2">Email</label>
              <input
                type="email"
                placeholder="you@example.com"
                {...register('email', {
                  required: 'Email is required',
                  pattern: {
                    value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                    message: 'Please enter a valid email'
                  }
                })}
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary focus:border-transparent"
              />
              {errors.email && <p className="text-red-600 text-sm mt-1">{errors.email.message}</p>}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-semibold mb-2">Password</label>
              <input
                type="password"
                placeholder="••••••••"
                {...register('password', {
                  required: 'Password is required',
                  minLength: {
                    value: 6,
                    message: 'Password must be at least 6 characters'
                  }
                })}
                className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-primary focus:border-transparent"
              />
              {errors.password && <p className="text-red-600 text-sm mt-1">{errors.password.message}</p>}
            </div>

            {/* Remember Me */}
            <div className="flex items-center">
              <input
                type="checkbox"
                id="remember"
                className="w-4 h-4 text-primary rounded"
              />
              <label htmlFor="remember" className="ml-2 text-sm text-gray-600">
                Remember me
              </label>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isSubmitting}
              onClick={handleSignInClick}
              className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {/* Divider */}
          <div className="my-6 relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">Or</span>
            </div>
          </div>

          {/* Sign Up Link */}
          <p className="text-center text-gray-600">
            Don't have an account?{' '}
            <Link href="/register" className="text-primary hover:text-secondary font-semibold">
              Sign up
            </Link>
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-white/70 text-sm mt-6">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  )
}
