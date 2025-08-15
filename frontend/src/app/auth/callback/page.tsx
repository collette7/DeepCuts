'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

export default function AuthCallback() {
  const router = useRouter()

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        const { error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('Auth callback error:', error)
          router.push('/?error=auth_failed')
          return
        }

        // Check for pending search query to restore
        const pendingQuery = sessionStorage.getItem('pendingSearchQuery')
        
        // Redirect to home page, preserving search if it exists
        if (pendingQuery) {
          // The page.tsx will handle restoring the search via useEffect
          router.push('/')
        } else {
          router.push('/?message=welcome')
        }
      } catch (err) {
        console.error('Unexpected error in auth callback:', err)
        router.push('/?error=unexpected')
      }
    }

    handleAuthCallback()
  }, [router])

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh',
      flexDirection: 'column'
    }}>
      <h2>Completing sign in...</h2>
      <p>Please wait a moment.</p>
    </div>
  )
}