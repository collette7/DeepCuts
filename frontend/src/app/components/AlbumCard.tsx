import { AlbumData } from '@/lib/api';
import { Music, Heart } from 'lucide-react';
import './AlbumCard.scss';

interface AlbumCardProps {
  album: AlbumData;
  onListenNow: (album: AlbumData) => void;
  onToggleFavorite?: (album: AlbumData) => void;
  isFavorited?: boolean;
  isLoading?: boolean;
}

export default function AlbumCard({ album, onListenNow, onToggleFavorite, isFavorited = false, isLoading = false }: AlbumCardProps) {
  const handleFavoriteClick = (e: React.MouseEvent) => {
    e.stopPropagation(); 
    if (onToggleFavorite && !isLoading) {
      onToggleFavorite(album);
    }
  };

  return (
    <div className="album-card" onClick={() => onListenNow(album)}>
      <div className="img-container">
        {album.cover_url ? (
          <img 
            className="cover-image" 
            src={album.cover_url} 
            alt={`${album.title} cover`}
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.style.display = 'none';
              const placeholder = target.nextElementSibling as HTMLElement;
              if (placeholder) placeholder.style.display = 'flex';
            }}
          />
        ) : null}
        <div className="cover-placeholder" style={{ display: album.cover_url ? 'none' : 'flex' }}>
          <Music className="cover-placeholder-icon" size={40} />
          <span className="cover-placeholder-text">Album Cover</span>
        </div>
        
        {/* Favorite Button */}
        {onToggleFavorite && (
          <button 
            onClick={handleFavoriteClick}
            disabled={isLoading}
            className={`favorite-btn ${isFavorited ? 'favorited' : ''} ${isLoading ? 'loading' : ''}`}
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
        <div className="album-metadata">
          {album.genre && album.genre !== "Unknown" && (
            <span className="metadata-item">{album.genre.toUpperCase()}</span>
          )}
          {album.genre && album.genre !== "Unknown" && album.year && (
            <span className="metadata-separator">•</span>
          )}
          {album.year && (
            <span className="metadata-item">{album.year}</span>
          )}
        </div>
      </div>
    </div>
  );
}