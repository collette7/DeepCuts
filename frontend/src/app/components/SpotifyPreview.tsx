'use client';

import { useState, useRef, useEffect } from 'react';
import { AlbumData } from '@/lib/api';

interface SpotifyPreviewProps {
  album: AlbumData | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function SpotifyPreview({ album, isOpen, onClose }: SpotifyPreviewProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(30);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setIsPlaying(false);
      setCurrentTime(0);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
    }
  }, [isOpen]);

  useEffect(() => {
    if (audioRef.current) {
      const audio = audioRef.current;
      
      const updateTime = () => setCurrentTime(audio.currentTime);
      const updateDuration = () => setDuration(audio.duration || 30);
      const handleEnded = () => setIsPlaying(false);
      
      audio.addEventListener('timeupdate', updateTime);
      audio.addEventListener('loadedmetadata', updateDuration);
      audio.addEventListener('ended', handleEnded);
      
      return () => {
        audio.removeEventListener('timeupdate', updateTime);
        audio.removeEventListener('loadedmetadata', updateDuration);
        audio.removeEventListener('ended', handleEnded);
      };
    }
  }, [album?.spotify_preview_url]);

  const togglePlayPause = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const progressPercentage = (currentTime / duration) * 100;

  if (!isOpen || !album) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="preview-backdrop" onClick={onClose} />
      
      {/* Flyout */}
      <div className="spotify-preview-flyout">
        <div className="preview-header">
          <h3>Album Details</h3>
          <button onClick={onClose} className="preview-close-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        
        <div className="preview-content">
          {/* Album Info */}
          <div className="preview-album-info">
            <div className="preview-album-cover">
              {album.cover_url ? (
                <img src={album.cover_url} alt={album.title} />
              ) : (
                <div className="preview-cover-placeholder">♪</div>
              )}
            </div>
            <div className="preview-album-details">
              <h4>{album.title}</h4>
              <p>{album.artist}</p>
              {album.year && <span className="preview-year">{album.year}</span>}
            </div>
          </div>

          {/* Audio Player */}
          {album.spotify_preview_url ? (
            <div className="preview-player">
              <audio
                ref={audioRef}
                src={album.spotify_preview_url}
                preload="metadata"
              />
              
              <div className="player-controls">
                <button 
                  onClick={togglePlayPause}
                  className="play-pause-btn"
                >
                  {isPlaying ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                      <rect x="6" y="4" width="4" height="16"/>
                      <rect x="14" y="4" width="4" height="16"/>
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                      <polygon points="5,3 19,12 5,21"/>
                    </svg>
                  )}
                </button>
                
                <div className="progress-section">
                  <span className="time-display">{formatTime(currentTime)}</span>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill"
                      style={{ width: `${progressPercentage}%` }}
                    />
                  </div>
                  <span className="time-display">{formatTime(duration)}</span>
                </div>
                
                <svg className="volume-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="11,5 6,9 2,9 2,15 6,15 11,19"/>
                  <path d="M19.07,4.93a10,10,0,0,1,0,14.14M15.54,8.46a5,5,0,0,1,0,7.07"/>
                </svg>
              </div>
              
              <p className="preview-note">30-second preview from Spotify</p>
            </div>
          ) : (
            <div className="no-preview">
              <svg className="no-preview-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="11,5 6,9 2,9 2,15 6,15 11,19"/>
                <path d="M19.07,4.93a10,10,0,0,1,0,14.14M15.54,8.46a5,5,0,0,1,0,7.07"/>
              </svg>
              <p>Why this album?</p>
              {album.reasoning ? (
                <div className="reasoning-text">
                  <p>{album.reasoning}</p>
                </div>
              ) : (
                <div className="reasoning-text">
                  <p style={{ fontStyle: 'italic', opacity: 0.7 }}>
                    No preview available. Try searching for AI-powered recommendations with personalized explanations!
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="preview-actions">
            {album.spotify_url && (
              <a 
                href={album.spotify_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="spotify-link-btn"
              >
                Open in Spotify
              </a>
            )}
            {album.discogs_url && (
              <a 
                href={album.discogs_url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="discogs-link-btn"
              >
                Buy on Discogs
              </a>
            )}
          </div>
        </div>
      </div>
    </>
  );
}