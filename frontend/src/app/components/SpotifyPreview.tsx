'use client';

import { useState, useRef, useEffect } from 'react';
import { AlbumData } from '@/lib/api';
import { X, Pause, Play, Volume2 } from 'lucide-react';

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
            <X size={16} />
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
              {album.year && <time className="preview-year" dateTime={album.year.toString()}>{album.year}</time>}
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
                    <Pause size={20} fill="currentColor" />
                  ) : (
                    <Play size={20} fill="currentColor" />
                  )}
                </button>
                
                <div className="progress-section">
                  <time className="time-display">{formatTime(currentTime)}</time>
                  <div className="progress-bar">
                    <div 
                      className="progress-fill"
                      style={{ width: `${progressPercentage}%` }}
                    />
                  </div>
                  <time className="time-display">{formatTime(duration)}</time>
                </div>
                
                <Volume2 className="volume-icon" size={16} />
              </div>
              
              <p className="preview-note">30-second preview from Spotify</p>
            </div>
          ) : (
            <div className="no-preview">
              <Volume2 className="no-preview-icon" size={24} />
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