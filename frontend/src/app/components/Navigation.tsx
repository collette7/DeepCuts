'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';
import AuthModal from './auth/AuthModal';
import { Menu, User } from 'lucide-react';
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
    <nav className="main-nav">
      <div className="nav-container">
        {/* Logo */}
        <button className="nav-logo" onClick={() => router.push('/')} aria-label="DeepCuts Home">
          <strong className="nav-logo-text">DeepCuts</strong>
        </button>


        {/* Right Menu */}
        <div className="nav-right">
          <div className="nav-user-menu">
            <button 
              className="nav-user-button"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              <Menu size={16} />
              
              {user ? (
                <div className="user-avatar">
                  {user.email?.charAt(0).toUpperCase()}
                </div>
              ) : (
                <User size={20} />
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