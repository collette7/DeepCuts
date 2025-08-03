'use client';

import { useState, useRef, useEffect } from 'react';
import { Cross2Icon, PlayIcon, PauseIcon, SpeakerLoudIcon } from '@radix-ui/react-icons';
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
            <Cross2Icon />
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
                  {isPlaying ? <PauseIcon /> : <PlayIcon />}
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
                
                <SpeakerLoudIcon className="volume-icon" />
              </div>
              
              <p className="preview-note">30-second preview from Spotify</p>
            </div>
          ) : (
            <div className="no-preview">
              <SpeakerLoudIcon className="no-preview-icon" />
              <p>Why this album?</p>
              {album.reasoning ? (
                <div className="reasoning-text">
                  <p>{album.reasoning}</p>
                </div>
              ) : (
                <span>This album doesn&apos;t have a preview on Spotify</span>
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