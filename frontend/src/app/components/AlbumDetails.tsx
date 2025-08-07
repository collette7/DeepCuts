'use client';

import { Cross2Icon, ExternalLinkIcon } from '@radix-ui/react-icons';
import { AlbumData } from '@/lib/api';

interface AlbumDetailsProps {
  album: AlbumData | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function AlbumDetails({ album, isOpen, onClose }: AlbumDetailsProps) {
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
            <Cross2Icon />
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
          {album.reasoning && (
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
            {album.spotify_url && (
              <a 
                href={album.spotify_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="spotify-action-btn"
              >
                <ExternalLinkIcon />
                Listen on Spotify
              </a>
            )}
          </div>
        </div>
      </div>
    </>
  );
}