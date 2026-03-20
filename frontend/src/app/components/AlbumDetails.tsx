'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
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
  hiderecommendationReason?: boolean;
}

const VINYL_COLORS = ['#FF8C00', '#FF4081', '#00BCD4', '#8BC34A', '#9C27B0', '#FF5722', '#00E5FF', '#E040FB', '#76FF03', '#FF6E40'];

function vinylColor(album: AlbumData | null): string {
  if (!album) return VINYL_COLORS[0];
  const seed = `${album.title || ''}|${album.artist || ''}`.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
  return VINYL_COLORS[seed % VINYL_COLORS.length];
}

export default function AlbumDetails({ album, isOpen, onClose, user, onAuthRequired, hiderecommendationReason = false }: AlbumDetailsProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const [closing, setClosing] = useState(false);
  const vinylStyle = { '--vinyl-color': vinylColor(album) } as React.CSSProperties;
  const [visible, setVisible] = useState(false);

  const handleClose = useCallback(() => {
    setClosing(true);
    setTimeout(() => {
      setClosing(false);
      setVisible(false);
      onClose();
    }, 300);
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      setVisible(true);
      setClosing(false);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!visible) return;
    closeButtonRef.current?.focus();
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [visible, handleClose]);

  if (!visible || !album) return null;

  return (
    <>
      <div className={`details-backdrop${closing ? ' closing' : ''}`} onClick={handleClose} aria-hidden="true" />
      
      <div className={`album-details-flyout${closing ? ' closing' : ''}`} role="dialog" aria-modal="true" aria-label={`${album.title} by ${album.artist}`}>
        <div className="details-header">
          <h3>Album Details</h3>
          <button ref={closeButtonRef} onClick={handleClose} className="details-close-btn" aria-label="Close album details">
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
                <div className="details-cover-placeholder">
                  <div className="vinyl-wrapper" style={vinylStyle}>
                    <div className="vinyl" />
                  </div>
                </div>
              )}
            </div>
            <div className="details-album-text">
              <h4>{album.title}</h4>
              <p>{album.artist}</p>
              {album.year && <time className="details-year" dateTime={album.year.toString()}>{album.year}</time>}
            </div>
          </div>

          {/* Recommendation Reasoning */}
          {!hiderecommendationReason && album.reasoning && (
            <div className="recommendation-section">
              <div className="recommendation-header">
                <h5>Why this album?</h5>
              </div>
              <div className="reasoning-content">
                <p>{album.reasoning}</p>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="details-actions">
            {user ? (
              <>
                {album.spotify_url && (
                  <a 
                    href={album.spotify_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="btn btn-spotify btn-full"
                  >
                    <ExternalLink size={16} />
                    Listen on Spotify
                  </a>
                )}
                
                {album.discogs_url && (
                  <a 
                    href={album.discogs_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="btn btn-discogs btn-full"
                  >
                    <ExternalLink size={16} />
                    View on Discogs
                  </a>
                )}
              </>
            ) : (
              <button
                onClick={onAuthRequired}
                className="btn btn-primary btn-full btn-pulse"
              >
                <UserPlus size={16} />
                Sign up to listen
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}