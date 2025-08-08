'use client';

import { AlbumData } from '@/lib/api';
import { User } from '@supabase/supabase-js';
import './AlbumDetails.scss';

interface AlbumDetailsProps {
  album: AlbumData | null;
  isOpen: boolean;
  onClose: () => void;
  user?: User | null;
  onAuthRequired?: () => void;
}

export default function AlbumDetails({ album, isOpen, onClose, user, onAuthRequired }: AlbumDetailsProps) {
  if (!isOpen || !album) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="details-backdrop" onClick={onClose} />
      
      {/* Flyout */}
      <div className="album-details-flyout">
        <div className="details-header">
          <h3>Album Details</h3>
          <button onClick={onClose} className="details-close-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        
        <div className="details-content">
          {/* Album Info */}
          <div className="details-album-info">
            <div className="details-album-cover">
              {album.cover_url ? (
                <img src={album.cover_url} alt={album.title} />
              ) : (
                <div className="details-cover-placeholder">♪</div>
              )}
            </div>
            <div className="details-album-text">
              <h4>{album.title}</h4>
              <p>{album.artist}</p>
              {album.year && <span className="details-year">{album.year}</span>}
            </div>
          </div>

          {/* Recommendation Reasoning */}
          <div className="recommendation-section">
            <div className="recommendation-header">
              <h5>Why this album?</h5>
            </div>
            <div className="reasoning-content">
              {album.reasoning ? (
                <p>{album.reasoning}</p>
              ) : (
                <p style={{ fontStyle: 'italic', opacity: 0.7 }}>
                  Discover new music through search to see AI-powered recommendations with personalized explanations!
                </p>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="details-actions">
            {album.spotify_url && (
              user ? (
                <a 
                  href={album.spotify_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="spotify-action-btn"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M18 13V6A2 2 0 0 0 16 4H4A2 2 0 0 0 2 6V18A2 2 0 0 0 4 20H16A2 2 0 0 0 18 18V13Z"/>
                    <polyline points="15,3 21,3 21,9"/>
                    <line x1="10" y1="14" x2="21" y2="3"/>
                  </svg>
                  Listen on Spotify
                </a>
              ) : (
                <button
                  onClick={onAuthRequired}
                  className="spotify-action-btn"
                  style={{ 
                    background: '#1db954',
                    border: 'none',
                    width: '100%',
                    cursor: 'pointer'
                  }}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 11L12 14L22 4"/>
                    <path d="M21 12V18A2 2 0 0 1 19 20H5A2 2 0 0 1 3 18V6A2 2 0 0 1 5 4H16"/>
                  </svg>
                  Sign up to Listen on Spotify
                </button>
              )
            )}
          </div>
        </div>
      </div>
    </>
  );
}