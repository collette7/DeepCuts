'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { pb } from '@/lib/pocketbase'

function AuthCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying')

  useEffect(() => {
    const confirmEmail = async () => {
      const token = searchParams.get('token')

      if (!token) {
        setStatus('error')
        return
      }

      try {
        await pb.collection('users').confirmVerification(token)
        setStatus('success')

        const pendingQuery = sessionStorage.getItem('pendingSearchQuery')
        setTimeout(() => {
          router.push(pendingQuery ? '/' : '/?message=welcome')
        }, 1500)
      } catch (err) {
        console.error('Email verification failed:', err)
        setStatus('error')
      }
    }

    confirmEmail()
  }, [router, searchParams])

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      flexDirection: 'column'
    }}>
      {status === 'verifying' && (
        <>
          <h2>Verifying your email...</h2>
          <p>Please wait a moment.</p>
        </>
      )}
      {status === 'success' && (
        <>
          <h2>Email verified!</h2>
          <p>Redirecting you now...</p>
        </>
      )}
      {status === 'error' && (
        <>
          <h2>Verification failed</h2>
          <p>This link may have expired. Please try signing up again or request a new verification email.</p>
        </>
      )}
    </div>
  )
}

export default function AuthCallback() {
  return (
    <Suspense fallback={null}>
      <AuthCallbackContent />
    </Suspense>
  )
}
