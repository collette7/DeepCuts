'use client'

import { useState } from 'react'
import { useAuth } from '@/app/contexts/AuthContext'

interface LoginFormProps {
  onSuccess?: () => void
  onSwitchToSignup?: () => void
}

export default function LoginForm({ onSuccess, onSwitchToSignup }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const { signIn } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const { error } = await signIn(email, password)
      
      if (error) {
        setError(error instanceof Error ? error.message : 'Invalid email or password')
      } else {
        onSuccess?.()
      }
    } catch {
      setError('Login failed')
    }
    
    setLoading(false)
  }

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <h2>Log in</h2>
      
      {error && (
        <div className="auth-error-message">
          {error}
        </div>
      )}

      <div className="auth-form-group">
        <label htmlFor="email">Email address</label>
        <input
          type="email"
          id="email"
          className="auth-form-input"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={loading}
        />
      </div>

      <div className="auth-form-group">
        <label htmlFor="password">Password</label>
        <input
          type="password"
          id="password"
          className="auth-form-input"
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          disabled={loading}
        />
      </div>

      <button type="submit" className="auth-submit-btn" disabled={loading}>
        {loading ? 'Logging in...' : 'Log in'}
      </button>

      <div className="auth-divider"></div>

      {onSwitchToSignup && (
        <p className="auth-switch">
          Don&apos;t have an account? <button type="button" className="auth-switch-btn" onClick={onSwitchToSignup}>Register here</button>
        </p>
      )}
      
      <div className="auth-help-links">
        <p>Trouble logging in? <button type="button" className="auth-help-link">Get help</button></p>
      </div>
    </form>
  )
}