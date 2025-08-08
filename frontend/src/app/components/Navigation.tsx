'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';
import AuthModal from './auth/AuthModal';
import './Navigation.scss';



export default function Navigation() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authView, setAuthView] = useState<'login' | 'signup'>('login');

  const handleSignOut = async () => {
    await signOut();
    setIsMenuOpen(false);
  };

  return (
    <nav className="airbnb-nav">
      <div className="nav-container">
        {/* Logo */}
        <div className="nav-logo" onClick={() => router.push('/')}>
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="16" fill="#FF5A5F"/>
            <path d="M16 8L20 12H18V20H14V12H12L16 8Z" fill="white"/>
          </svg>
          <span className="nav-logo-text">DeepCuts</span>
        </div>


        {/* Right Menu */}
        <div className="nav-right">
          <div className="nav-user-menu">
            <button 
              className="nav-user-button"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path 
                  d="M2 4.75C2 4.33579 2.33579 4 2.75 4H13.25C13.6642 4 14 4.33579 14 4.75C14 5.16421 13.6642 5.5 13.25 5.5H2.75C2.33579 5.5 2 5.16421 2 4.75Z" 
                  fill="currentColor"
                />
                <path 
                  d="M2 8C2 7.58579 2.33579 7.25 2.75 7.25H13.25C13.6642 7.25 14 7.58579 14 8C14 8.41421 13.6642 8.75 13.25 8.75H2.75C2.33579 8.75 2 8.41421 2 8Z" 
                  fill="currentColor"
/>
                <path 
                  d="M2.75 10.5C2.33579 10.5 2 10.8358 2 11.25C2 11.6642 2.33579 12 2.75 12H13.25C13.6642 12 14 11.6642 14 11.25C14 10.8358 13.6642 10.5 13.25 10.5H2.75Z" 
                  fill="currentColor"
                />
              </svg>
              
              {user ? (
                <div className="user-avatar">
                  {user.email?.charAt(0).toUpperCase()}
                </div>
              ) : (
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <circle cx="10" cy="8" r="3" fill="currentColor"/>
                  <path 
                    d="M4 18c0-3.314 2.686-6 6-6s6 2.686 6 6v1H4v-1z" 
                    fill="currentColor"
                  />
                </svg>
              )}
            </button>

            {isMenuOpen && (
              <>
                <div 
                  className="menu-backdrop" 
                  onClick={() => setIsMenuOpen(false)}
                />
                <div className="user-menu-dropdown">
                  {user ? (
                    <>
                      <div className="menu-item user-info">
                        <strong>{user.email}</strong>
                      </div>
                      <div className="menu-divider" />
                      <button 
                        className="menu-item"
                        onClick={() => {
                          router.push('/favorites');
                          setIsMenuOpen(false);
                        }}
                      >
                        My Favorites
                      </button>
                      <div className="menu-divider" />
                      <button 
                        className="menu-item"
                        onClick={handleSignOut}
                      >
                        Sign out
                      </button>
                    </>
                  ) : (
                    <>
                      <button 
                        className="menu-item"
                        onClick={() => {
                          setAuthView('signup');
                          setAuthModalOpen(true);
                          setIsMenuOpen(false);
                        }}
                      >
                        Sign up
                      </button>
                      <button 
                        className="menu-item"
                        onClick={() => {
                          setAuthView('login');
                          setAuthModalOpen(true);
                          setIsMenuOpen(false);
                        }}
                      >
                        Log in
                      </button>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
      
      <AuthModal 
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        defaultView={authView}
      />
    </nav>
  );
}