// Global auth error handler for dealing with an invalid/expired session.
// PocketBase doesn't have Supabase's separate refresh-token concept — its
// tokens are self-contained JWTs, and a 401 on an authenticated request
// (or on authRefresh()) is the equivalent "session is no longer valid"
// signal.
import { pb } from './pocketbase'

export class AuthError extends Error {
  constructor(message: string, public code?: string) {
    super(message)
    this.name = 'AuthError'
  }
}

export function isRefreshTokenError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false

  const errorObj = error as { status?: number }
  return errorObj.status === 401
}

export function handleAuthError(error: unknown): void {
  if (isRefreshTokenError(error)) {
    console.warn('Session invalid, signing out user')

    pb.authStore.clear()

    if (typeof window !== 'undefined') {
      window.location.reload()
    }
  }
}

// Global error handler that can be attached to window
export function setupGlobalAuthErrorHandler() {
  if (typeof window !== 'undefined') {
    // Also handle unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      if (isRefreshTokenError(event.reason)) {
        handleAuthError(event.reason)
        event.preventDefault()
      }
    })
  }
}
