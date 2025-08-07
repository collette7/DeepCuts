'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import * as Separator from '@radix-ui/react-separator';
import './Navigation.css';

interface NavigationProps {
  onSearch?: (query: string) => void | Promise<void>;
  searchQuery?: string;
}

export default function Navigation({ onSearch, searchQuery }: NavigationProps) {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [currentSearch, setCurrentSearch] = useState(searchQuery || '');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch && currentSearch.trim()) {
      await onSearch(currentSearch.trim());
    }
  };

  const handleSignOut = async () => {
    await signOut();
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

        {/* Search Bar */}
        <div className="nav-search">
          <form onSubmit={handleSearch} className="search-form">
            <button type="button" className="search-section search-where">
              <div className="search-section-content">
                <span className="search-label">Discover</span>
                <input 
                  type="text"
                  placeholder="Albums, artists, genres..."
                  value={currentSearch}
                  onChange={(e) => setCurrentSearch(e.target.value)}
                  className="search-input"
                />
              </div>
            </button>
            
            <div className="search-divider" />
            
            <button type="button" className="search-section search-when">
              <div className="search-section-content">
                <span className="search-label">Era</span>
                <span className="search-placeholder">Any decade</span>
              </div>
            </button>
            
            <div className="search-divider" />
            
            <button type="button" className="search-section search-who">
              <div className="search-section-content">
                <span className="search-label">Vibe</span>
                <span className="search-placeholder">Any mood</span>
              </div>
            </button>

            <button type="submit" className="search-button">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path 
                  d="M7.5 2.75C5.01472 2.75 3 4.76472 3 7.25C3 9.73528 5.01472 11.75 7.5 11.75C8.45278 11.75 9.33139 11.4653 10.0625 10.9844L12.5391 13.4609C12.832 13.7539 13.3068 13.7539 13.5998 13.4609C13.8927 13.168 13.8927 12.6932 13.5998 12.4002L11.1233 9.92366C11.6042 9.19252 11.8889 8.31391 11.8889 7.36111H12V7.25C12 4.76472 9.98528 2.75 7.5 2.75ZM7.5 4.25C9.15685 4.25 10.5 5.59315 10.5 7.25C10.5 8.90685 9.15685 10.25 7.5 10.25C5.84315 10.25 4.5 8.90685 4.5 7.25C4.5 5.59315 5.84315 4.25 7.5 4.25Z" 
                  fill="white"
                />
              </svg>
            </button>
          </form>
        </div>

        {/* Right Menu */}
        <div className="nav-right">
          <button className="nav-host-link">
            Suggest an artist
          </button>
          
          <div className="nav-user-menu">
            <DropdownMenu.Root>
              <DropdownMenu.Trigger asChild>
                <button className="nav-user-button">
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
              </DropdownMenu.Trigger>

              <DropdownMenu.Portal>
                <DropdownMenu.Content className="user-menu-dropdown" sideOffset={8} align="end">
                  {user ? (
                    <>
                      <DropdownMenu.Item className="menu-item user-info" onSelect={(e) => e.preventDefault()}>
                        <strong>{user.email}</strong>
                      </DropdownMenu.Item>
                      <Separator.Root className="menu-divider" />
                      <DropdownMenu.Item 
                        className="menu-item"
                        onSelect={() => router.push('/favorites')}
                      >
                        My Favorites
                      </DropdownMenu.Item>
                      <DropdownMenu.Item 
                        className="menu-item"
                        onSelect={() => router.push('/recommendations')}
                      >
                        Recommendation History
                      </DropdownMenu.Item>
                      <Separator.Root className="menu-divider" />
                      <DropdownMenu.Item 
                        className="menu-item"
                        onSelect={handleSignOut}
                      >
                        Sign out
                      </DropdownMenu.Item>
                    </>
                  ) : (
                    <>
                      <DropdownMenu.Item 
                        className="menu-item"
                        onSelect={() => console.log('Sign up clicked')}
                      >
                        Sign up
                      </DropdownMenu.Item>
                      <DropdownMenu.Item 
                        className="menu-item"
                        onSelect={() => console.log('Log in clicked')}
                      >
                        Log in
                      </DropdownMenu.Item>
                    </>
                  )}
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>
          </div>
        </div>
      </div>
    </nav>
  );
}