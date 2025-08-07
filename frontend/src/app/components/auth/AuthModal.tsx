'use client'

import { useState } from 'react'
import LoginForm from './LoginForm'
import SignupForm from './SignupForm'
import './AuthModal.css'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  defaultView?: 'login' | 'signup'
}

export default function AuthModal({ isOpen, onClose, defaultView = 'login' }: AuthModalProps) {
  const [currentView, setCurrentView] = useState<'login' | 'signup'>(defaultView)

  if (!isOpen) return null

  const handleSuccess = () => {
    onClose()
  }

  return (
    <div className="auth-modal-overlay" onClick={onClose}>
      <div className="auth-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="auth-modal-close" onClick={onClose}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="m18 6-12 12"/>
            <path d="m6 6 12 12"/>
          </svg>
        </button>
        
        {currentView === 'login' ? (
          <LoginForm 
            onSuccess={handleSuccess}
            onSwitchToSignup={() => setCurrentView('signup')}
          />
        ) : (
          <SignupForm 
            onSuccess={handleSuccess}
            onSwitchToLogin={() => setCurrentView('login')}
          />
        )}
      </div>
    </div>
  )
}