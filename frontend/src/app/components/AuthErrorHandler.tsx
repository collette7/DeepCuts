'use client'

import { useEffect } from 'react'
import { setupGlobalAuthErrorHandler } from '@/lib/auth-error-handler'

export default function AuthErrorHandler() {
  useEffect(() => {
    setupGlobalAuthErrorHandler()
  }, [])

  return null // This component doesn't render anything
}