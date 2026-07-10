'use client'

import { createContext, useContext, useEffect, useState } from 'react'
import { pb, type AuthenticatedUser } from '@/lib/pocketbase'

interface AuthContextType {
  user: AuthenticatedUser | null
  loading: boolean
  signUp: (email: string, password: string) => Promise<{ error: unknown }>
  signIn: (email: string, password: string) => Promise<{ error: unknown }>
  signOut: () => Promise<void>
  clearSession: () => void
  requestPasswordReset: (email: string) => Promise<{ error: unknown }>
  confirmPasswordReset: (token: string, password: string) => Promise<{ error: unknown }>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(
    pb.authStore.isValid ? (pb.authStore.record as AuthenticatedUser) : null
  )
  const [loading, setLoading] = useState(true)

  const clearSession = () => {
    pb.authStore.clear()
    setUser(null)
  }

  useEffect(() => {
    // PocketBase's SDK persists the token to localStorage but doesn't
    // auto-refresh it on a timer the way Supabase did — verify it's still
    // valid on load and clear state if the token expired or the account
    // was removed server-side.
    const verifySession = async () => {
      if (pb.authStore.isValid) {
        try {
          await pb.collection('users').authRefresh()
          setUser(pb.authStore.record as AuthenticatedUser)
        } catch {
          clearSession()
        }
      }
      setLoading(false)
    }
    verifySession()

    const unsubscribe = pb.authStore.onChange((_token, record) => {
      setUser(record as AuthenticatedUser | null)
    })

    const handleSessionExpired = () => clearSession()
    window.addEventListener('auth:sessionExpired', handleSessionExpired)

    return () => {
      unsubscribe()
      window.removeEventListener('auth:sessionExpired', handleSessionExpired)
    }
  }, [])

  const signUp = async (email: string, password: string) => {
    try {
      await pb.collection('users').create({ email, password, passwordConfirm: password })
      await pb.collection('users').requestVerification(email)
      return { error: null }
    } catch (error) {
      return { error }
    }
  }

  const signIn = async (email: string, password: string) => {
    try {
      await pb.collection('users').authWithPassword(email, password)
      return { error: null }
    } catch (error) {
      return { error }
    }
  }

  const signOut = async () => {
    clearSession()
  }

  const requestPasswordReset = async (email: string) => {
    try {
      await pb.collection('users').requestPasswordReset(email)
      return { error: null }
    } catch (error) {
      return { error }
    }
  }

  const confirmPasswordReset = async (token: string, password: string) => {
    try {
      await pb.collection('users').confirmPasswordReset(token, password, password)
      return { error: null }
    } catch (error) {
      return { error }
    }
  }

  const value = {
    user,
    loading,
    signUp,
    signIn,
    signOut,
    clearSession,
    requestPasswordReset,
    confirmPasswordReset,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
