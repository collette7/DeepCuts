import * as Avatar from '@radix-ui/react-avatar';
import { DiscIcon, HeartIcon, HeartFilledIcon } from '@radix-ui/react-icons';
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
        <Avatar.Root className="cover-placeholder">
          <Avatar.Image 
            className="cover-image" 
            src={album.cover_url || ''} 
            alt={`${album.title} cover`}
          />
          <Avatar.Fallback className="cover-placeholder">
            <DiscIcon className="cover-placeholder-icon" />
            <span className="cover-placeholder-text">Album Cover</span>
          </Avatar.Fallback>
        </Avatar.Root>
        
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
              <HeartFilledIcon />
            ) : (
              <HeartIcon />
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