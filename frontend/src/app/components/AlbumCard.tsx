import { AlbumData } from '@/lib/api';
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
      <div className="album-cover">
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
          <svg className="cover-placeholder-icon" width="40" height="40" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L15 1H5C3.89 1 3 1.89 3 3V21A2 2 0 0 0 5 23H19A2 2 0 0 0 21 21V9M19 9H14V4H15.5L19 7.5V9Z" />
          </svg>
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
            ) : isFavorited ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 21.35L10.55 20.03C5.4 15.36 2 12.27 2 8.5C2 5.41 4.42 3 7.5 3C9.24 3 10.91 3.81 12 5.08C13.09 3.81 14.76 3 16.5 3C19.58 3 22 5.41 22 8.5C22 12.27 18.6 15.36 13.45 20.03L12 21.35Z" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20.84 4.61A5.5 5.5 0 0 0 16.5 3C14.76 3 13.09 3.81 12 5.08C10.91 3.81 9.24 3 7.5 3A5.5 5.5 0 0 0 2.16 4.61C1.14 6.27 1.14 8.73 2.16 10.39L12 21.35L21.84 10.39C22.86 8.73 22.86 6.27 20.84 4.61Z" />
              </svg>
            )}
          </button>
        )}
      </div>
      <div className="album-content">
        <div className="album-header">
          <h3 className="album-title">{album.title}</h3>
          <p className="album-artist">by {album.artist}</p>
        </div>
        <div className="album-details">
          {album.year && (
            <span className="album-year">{album.year}</span>
          )}
          {album.genre && album.genre !== "Unknown" && (
            <span className="album-genre">{album.genre}</span>
          )}
        </div>
      </div>
    </div>
  );
}