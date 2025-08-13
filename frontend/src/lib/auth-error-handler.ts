// Global auth error handler for dealing with refresh token issues
import { supabase } from './supabase'

export class AuthError extends Error {
  constructor(message: string, public code?: string) {
    super(message)
    this.name = 'AuthError'
  }
}

export function isRefreshTokenError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false
  
  const errorObj = error as { message?: string; code?: string }
  
  return (
    (typeof errorObj.message === 'string' && (
      errorObj.message.includes('refresh_token_not_found') ||
      errorObj.message.includes('Invalid Refresh Token') ||
      errorObj.message.includes('Refresh Token Not Found')
    )) ||
    errorObj.code === 'refresh_token_not_found'
  )
}

export async function handleAuthError(error: unknown): Promise<void> {
  if (isRefreshTokenError(error)) {
    const errorMessage = error && typeof error === 'object' && 'message' in error 
      ? (error as { message: string }).message 
      : 'Unknown refresh token error'
    console.warn('Refresh token error detected, signing out user:', errorMessage)
    
    try {
      // Sign out the user to clear invalid session
      await supabase.auth.signOut()
      
      // Clear any local storage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('supabase.auth.token')
        sessionStorage.clear()
      }
      
      // Optionally reload the page to reset the app state
      if (typeof window !== 'undefined') {
        window.location.reload()
      }
    } catch (signOutError) {
      console.error('Error during auth cleanup:', signOutError)
    }
  }
}

// Global error handler that can be attached to window
export function setupGlobalAuthErrorHandler() {
  if (typeof window !== 'undefined') {
    const originalConsoleError = console.error
    
    console.error = (...args: unknown[]) => {
      const error = args[0]
      if (isRefreshTokenError(error)) {
        handleAuthError(error)
      }
      originalConsoleError.apply(console, args)
    }
    
    // Also handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      if (isRefreshTokenError(event.reason)) {
        handleAuthError(event.reason)
        event.preventDefault()
      }
    })
  }
}