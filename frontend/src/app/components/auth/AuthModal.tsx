'use client'

import { useState, useEffect, useRef } from 'react'
import { X, Mail } from 'lucide-react'
import { pb } from '@/lib/pocketbase'
import { useAuth } from '@/app/contexts/AuthContext'
import LoginForm from './LoginForm'
import SignupForm from './SignupForm'
import './AuthModal.scss'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  defaultView?: 'login' | 'signup'
}

export default function AuthModal({ isOpen, onClose, defaultView = 'login' }: AuthModalProps) {
  const [currentView, setCurrentView] = useState<'login' | 'signup' | 'verify-email' | 'forgot-password'>(defaultView)
  const [userEmail, setUserEmail] = useState('')
  const [resendStatus, setResendStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [resetEmail, setResetEmail] = useState('')
  const [resetStatus, setResetStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const { requestPasswordReset } = useAuth()

  useEffect(() => {
    setCurrentView(defaultView)
  }, [defaultView])

  useEffect(() => {
    if (!isOpen) return
    closeButtonRef.current?.focus()
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const handleSuccess = () => {
    onClose()
  }

  const handleSignupSuccess = (email: string) => {
    setUserEmail(email)
    setCurrentView('verify-email')
    setResendStatus('idle')
  }

  const handleResendVerification = async () => {
    if (resendStatus === 'sending') return
    setResendStatus('sending')
    try {
      await pb.collection('users').requestVerification(userEmail)
      setResendStatus('sent')
    } catch {
      setResendStatus('error')
    }
  }

  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (resetStatus === 'sending') return
    setResetStatus('sending')
    const { error } = await requestPasswordReset(resetEmail)
    setResetStatus(error ? 'error' : 'sent')
  }

  const renderContent = () => {
    switch (currentView) {
      case 'login':
        return (
          <LoginForm
            onSuccess={handleSuccess}
            onSwitchToSignup={() => setCurrentView('signup')}
            onForgotPassword={() => setCurrentView('forgot-password')}
          />
        )
      case 'signup':
        return (
          <SignupForm 
            onSwitchToLogin={() => setCurrentView('login')}
            onSignupSuccess={handleSignupSuccess}
          />
        )
      case 'verify-email':
        return (
          <div className="email-verification-screen">
            <div className="email-verification-icon">
              <Mail size={48} />
            </div>
            
            <h2>Check your email</h2>
            
            <div className="email-verification-message">
              <p>We&apos;ve sent a verification link to:</p>
              <strong>{userEmail}</strong>
              <p>Click the link in the email to verify your account and start discovering music.</p>
            </div>

            <div className="email-verification-help">
              <p>
                Didn&apos;t receive the email? Check your spam folder or{' '}
                <button
                  className="resend-link"
                  onClick={handleResendVerification}
                  disabled={resendStatus === 'sending'}
                >
                  {resendStatus === 'sending' ? 'Sending...' : resendStatus === 'sent' ? 'Sent!' : 'resend verification'}
                </button>
              </p>
              {resendStatus === 'error' && (
                <p className="auth-error-message">Failed to resend. Please try again.</p>
              )}
            </div>

            <button 
              className="btn btn-secondary btn-full"
              onClick={handleSuccess}
            >
              Close
            </button>
          </div>
        )
      case 'forgot-password':
        return (
          <form onSubmit={handleForgotPasswordSubmit} className="auth-form">
            <h2>Reset your password</h2>

            {resetStatus === 'sent' ? (
              <div className="email-verification-message">
                <p>If an account exists for:</p>
                <strong>{resetEmail}</strong>
                <p>we&apos;ve sent a link to reset your password.</p>
              </div>
            ) : (
              <>
                <div className="auth-form-group">
                  <label htmlFor="reset-email">Email address</label>
                  <input
                    type="email"
                    id="reset-email"
                    className="auth-form-input"
                    placeholder="Enter your account email"
                    value={resetEmail}
                    onChange={(e) => setResetEmail(e.target.value)}
                    required
                    disabled={resetStatus === 'sending'}
                  />
                </div>
                {resetStatus === 'error' && (
                  <div className="auth-error-message">Something went wrong. Please try again.</div>
                )}
                <button type="submit" className="btn btn-primary btn-full" disabled={resetStatus === 'sending'}>
                  {resetStatus === 'sending' ? 'Sending...' : 'Send reset link'}
                </button>
              </>
            )}

            <div className="auth-help-links">
              <button type="button" className="auth-help-link" onClick={() => setCurrentView('login')}>
                Back to log in
              </button>
            </div>
          </form>
        )
      default:
        return null
    }
  }

  return (
    <>
      <div className="auth-modal-overlay" onClick={onClose} aria-hidden="true" />
      <div className="auth-modal-content" role="dialog" aria-modal="true" aria-label="Authentication" onClick={(e) => e.stopPropagation()}>
        <button ref={closeButtonRef} className="auth-modal-close" onClick={onClose} aria-label="Close">
          <X size={16} />
        </button>
        {renderContent()}
      </div>
    </>
  )
}