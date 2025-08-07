'use client'

import { useState } from 'react'
import { useAuth } from '@/app/contexts/AuthContext'

interface SignupFormProps {
  onSuccess?: () => void
  onSwitchToLogin?: () => void
}

export default function SignupForm({ onSuccess, onSwitchToLogin }: SignupFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const { signUp } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      setLoading(false)
      return
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters')
      setLoading(false)
      return
    }

    try {
      const { error } = await signUp(email, password)
      
      if (error) {
        setError(error instanceof Error ? error.message : 'Signup failed')
      } else {
        onSuccess?.()
      }
    } catch {
      setError('Signup failed')
    }
    
    setLoading(false)
  }

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <h2>Sign up</h2>
      
      {error && (
        <div className="auth-error-message">
          {error}
        </div>
      )}

      <div className="auth-form-group">
        <label htmlFor="signup-email">Email address</label>
        <input
          type="email"
          id="signup-email"
          className="auth-form-input"
          placeholder="Enter your email address"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={loading}
        />
      </div>

      <div className="auth-form-group">
        <label htmlFor="signup-password">Password</label>
        <input
          type="password"
          id="signup-password"
          className="auth-form-input"
          placeholder="Create a password (min 6 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={loading}
        />
      </div>

      <div className="auth-form-group">
        <label htmlFor="signup-confirm-password">Confirm Password</label>
        <input
          type="password"
          id="signup-confirm-password"
          className="auth-form-input"
          placeholder="Confirm your password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
          disabled={loading}
        />
      </div>

      <button type="submit" className="auth-submit-btn" disabled={loading}>
        {loading ? 'Creating account...' : 'Sign up'}
      </button>

      <div className="auth-divider"></div>

      {onSwitchToLogin && (
        <p className="auth-switch">
          Already have an account? <button type="button" className="auth-switch-btn" onClick={onSwitchToLogin}>Log in</button>
        </p>
      )}
      
      <div className="auth-help-links">
        <p>Trouble signing up? <button type="button" className="auth-help-link">Get help</button></p>
      </div>
    </form>
  )
}