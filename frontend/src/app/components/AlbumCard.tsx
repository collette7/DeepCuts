import { useState, useCallback } from 'react';
import { AlbumData } from '@/lib/api';
import { Music, Heart } from 'lucide-react';
import './AlbumCard.scss';

interface AlbumCardProps {
  album: AlbumData;
  onListenNow: (album: AlbumData) => void;
  onToggleFavorite?: (album: AlbumData) => void;
  isFavorited?: boolean;
  isLoading?: boolean;
  index?: number;
}

const VINYL_COLORS = ['#FF8C00', '#FF4081', '#00BCD4', '#8BC34A', '#9C27B0', '#FF5722', '#00E5FF', '#E040FB', '#76FF03', '#FF6E40'];

function vinylColor(album: AlbumData): string {
  const seed = `${album.title || ''}|${album.artist || ''}`.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
  return VINYL_COLORS[seed % VINYL_COLORS.length];
}

export default function AlbumCard({ album, onListenNow, onToggleFavorite, isFavorited = false, isLoading = false, index }: AlbumCardProps) {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [bouncing, setBouncing] = useState(false);
  const vinylStyle = { '--vinyl-color': vinylColor(album) } as React.CSSProperties;

  const handleImageLoad = useCallback(() => {
    setImageLoaded(true);
  }, []);

  const handleFavoriteClick = (e: React.MouseEvent) => {
    e.stopPropagation(); 
    if (onToggleFavorite && !isLoading) {
      setBouncing(true);
      setTimeout(() => setBouncing(false), 400);
      onToggleFavorite(album);
    }
  };

  return (
    <div
      className="album-card"
      style={{ animationDelay: `${(index || 0) * 60}ms` }}
      onClick={() => onListenNow(album)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onListenNow(album); } }}
      role="button"
      tabIndex={0}
    >
      <div className="img-container">
        {album.cover_url ? (
          <img 
            className={`cover-image${imageLoaded ? ' loaded' : ''}`}
            src={album.cover_url} 
            alt={`${album.title} cover`}
            onLoad={handleImageLoad}
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
              const placeholder = target.nextElementSibling as HTMLElement;
              if (placeholder) placeholder.style.display = 'flex';
            }}
          />
        ) : null}
        <div className="cover-placeholder" style={{ display: album.cover_url ? 'none' : 'flex' }}>
          <div className="vinyl-wrapper" style={vinylStyle}>
            <div className="vinyl" />
          </div>
        </div>
        
        {onToggleFavorite && (
          <button 
            onClick={handleFavoriteClick}
            disabled={isLoading}
            className={`favorite-btn ${isFavorited ? 'favorited' : ''} ${isLoading ? 'loading' : ''} ${bouncing ? 'bouncing' : ''}`}
            aria-label={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
          >
            {isLoading ? (
              <div className="spinner" />
            ) : (
              <Heart 
                size={18} 
                fill={isFavorited ? "currentColor" : "none"} 
                stroke="currentColor" 
                strokeWidth={1.5}
              />
            )}
          </button>
        )}
      </div>
      <div className="album-info">
        <div className="album-text">
          <h3 className="album-title">{album.title}</h3>
          <p className="album-artist">{album.artist}</p>
        </div>
        <dl className="album-metadata">
          {album.genre && album.genre !== "Unknown" && (
            <>
              <dt className="sr-only">Genre</dt>
              <dd className="metadata-item metadata-genre">{album.genre.split(',')[0].trim().toUpperCase()}</dd>
            </>
          )}
          {album.genre && album.genre !== "Unknown" && album.year && (
            <dd className="metadata-separator" aria-hidden="true">•</dd>
          )}
          {album.year && (
            <>
              <dt className="sr-only">Year</dt>
              <dd className="metadata-item metadata-year">{album.year}</dd>
            </>
          )}
        </dl>
      </div>
    </div>
  );
}