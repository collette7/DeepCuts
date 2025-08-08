'use client';

import { AlbumData } from '@/lib/api';
import { User } from '@supabase/supabase-js';
import { X, ExternalLink, UserPlus } from 'lucide-react';
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
            <X size={16} />
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
                  <ExternalLink size={16} />
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
                  <UserPlus size={16} />
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