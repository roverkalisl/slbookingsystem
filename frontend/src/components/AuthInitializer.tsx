'use client'

import { useEffect } from 'react'
import { useAuth } from '@/stores/auth'

export function AuthInitializer() {
  const initializeAuth = useAuth((state) => state.initializeAuth)

  useEffect(() => {
    void initializeAuth()
  }, [initializeAuth])

  return null
}