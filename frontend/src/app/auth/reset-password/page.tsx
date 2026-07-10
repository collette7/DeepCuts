'use client'

import { Suspense, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/app/contexts/AuthContext'
import '@/app/components/auth/LoginForm.scss'

function ResetPasswordForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { confirmPasswordReset } = useAuth()

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const token = searchParams.get('token')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!token) {
      setError('This reset link is missing its token. Please request a new one.')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setLoading(true)
    const { error: resetError } = await confirmPasswordReset(token, password)
    setLoading(false)

    if (resetError) {
      setError('This link may have expired. Please request a new password reset.')
      return
    }

    setSuccess(true)
    setTimeout(() => router.push('/'), 1500)
  }

  if (!token) {
    return (
      <div className="auth-form" style={{ maxWidth: 400, margin: '4rem auto' }}>
        <h2>Invalid reset link</h2>
        <p>This password reset link is missing its token. Please request a new one.</p>
      </div>
    )
  }

  if (success) {
    return (
      <div className="auth-form" style={{ maxWidth: 400, margin: '4rem auto' }}>
        <h2>Password updated</h2>
        <p>Redirecting you now...</p>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="auth-form" style={{ maxWidth: 400, margin: '4rem auto' }}>
      <h2>Set a new password</h2>

      {error && <div className="auth-error-message">{error}</div>}

      <div className="auth-form-group">
        <label htmlFor="new-password">New password</label>
        <input
          type="password"
          id="new-password"
          className="auth-form-input"
          placeholder="At least 8 characters"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={loading}
        />
      </div>

      <div className="auth-form-group">
        <label htmlFor="confirm-new-password">Confirm new password</label>
        <input
          type="password"
          id="confirm-new-password"
          className="auth-form-input"
          placeholder="Confirm your new password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
          disabled={loading}
        />
      </div>

      <button type="submit" className="btn btn-primary btn-full" disabled={loading}>
        {loading ? 'Updating...' : 'Update password'}
      </button>
    </form>
  )
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  )
}
