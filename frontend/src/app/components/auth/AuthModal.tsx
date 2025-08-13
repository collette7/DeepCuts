'use client'

import { useState, useEffect } from 'react'
import { X, Mail } from 'lucide-react'
import LoginForm from './LoginForm'
import SignupForm from './SignupForm'
import './AuthModal.scss'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  defaultView?: 'login' | 'signup'
}

export default function AuthModal({ isOpen, onClose, defaultView = 'login' }: AuthModalProps) {
  const [currentView, setCurrentView] = useState<'login' | 'signup' | 'verify-email'>(defaultView)
  const [userEmail, setUserEmail] = useState('')

  // Sync currentView with defaultView when it changes
  useEffect(() => {
    setCurrentView(defaultView)
  }, [defaultView])

  if (!isOpen) return null

  const handleSuccess = () => {
    onClose()
  }

  const handleSignupSuccess = (email: string) => {
    setUserEmail(email)
    setCurrentView('verify-email')
  }

  const renderContent = () => {
    switch (currentView) {
      case 'login':
        return (
          <LoginForm 
            onSuccess={handleSuccess}
            onSwitchToSignup={() => setCurrentView('signup')}
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
              <p>Didn&apos;t receive the email? Check your spam folder or <button className="resend-link">resend verification</button></p>
            </div>

            <button 
              className="btn btn-secondary btn-full"
              onClick={handleSuccess}
            >
              Close
            </button>
          </div>
        )
      default:
        return null
    }
  }

  return (
    <div className="auth-modal-overlay" onClick={onClose}>
      <div className="auth-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="auth-modal-close" onClick={onClose}>
          <X size={16} />
        </button>
        
        {renderContent()}
      </div>
    </div>
  )
}