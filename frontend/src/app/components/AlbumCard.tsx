import * as Avatar from '@radix-ui/react-avatar';
import { DiscIcon, PlayIcon } from '@radix-ui/react-icons';
import { AlbumData } from '@/lib/api';

interface AlbumCardProps {
  album: AlbumData;
  onListenNow: (album: AlbumData) => void;
}

export default function AlbumCard({ album, onListenNow }: AlbumCardProps) {
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