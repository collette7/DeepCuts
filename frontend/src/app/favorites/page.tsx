'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';
import { apiClient, AlbumData, FavoriteItem } from '@/lib/api';
import AlbumCard from '../components/AlbumCard';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorMessage from '../components/ui/ErrorMessage';
import AlbumDetails from '../components/AlbumDetails';


export default function FavoritesPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlbum, setSelectedAlbum] = useState<AlbumData | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [removingIds, setRemovingIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (user) {
      loadFavorites();
    } else {
      // Redirect to home if not logged in
      router.push('/');
    }
  }, [user]);

  const loadFavorites = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.getFavoritesWithDetails();
      
      if (response.success && response.favorites) {
        setFavorites(response.favorites);
      } else {
        setError('Failed to load favorites');
      }
    } catch (error) {
      console.error('Error loading favorites:', error);
      setError('Failed to load your favorites. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleListenNow = (album: AlbumData) => {
    setSelectedAlbum(album);
    setDetailsOpen(true);
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
    setSelectedAlbum(null);
  };

  const handleRemoveFavorite = async (album: AlbumData) => {
    if (removingIds.has(album.id)) return;

    setRemovingIds(prev => new Set(prev).add(album.id));
    
    try {
      await apiClient.removeFromFavorites(album.id);
      
      // Remove from local state
      setFavorites(prev => prev.filter(fav => {
        const favAlbum = fav.albums || fav.album;
        return favAlbum?.id !== album.id;
      }));
    } catch (error) {
      console.error(`Error removing favorite:`, error);
    } finally {
      setRemovingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(album.id);
        return newSet;
      });
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="container">
          <LoadingSpinner />
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="page-container">
      <div className="container">
        <header className="header">
          <div>
            <h1>Your Favorites</h1>
            <p>{favorites.length} albums saved</p>
          </div>
          <div className="auth-controls">
            <div className="auth-buttons">
              <button onClick={() => router.push('/')}>Back to Home</button>
            </div>
          </div>
        </header>

        {error && <ErrorMessage error={error} />}

        {!error && favorites.length === 0 && (
          <div className="empty-state">
            <h2>No favorites yet</h2>
            <p>Start exploring music and save albums you love!</p>
            <button onClick={() => router.push('/')}>
              Discover Music
            </button>
          </div>
        )}

        {!error && favorites.length > 0 && (
          <div className="favorites-section">
            <div className="albums-grid">
              {favorites.map((favorite) => {
                // Handle different response formats
                const album = favorite.albums || favorite.album;
                
                if (!album) return null; // Skip if no album data
                
                return (
                  <AlbumCard 
                    key={favorite.id || album.id}
                    album={album}
                    onListenNow={handleListenNow}
                    onToggleFavorite={handleRemoveFavorite}
                    isFavorited={true}
                    isLoading={removingIds.has(album.id)}
                  />
                );
              })}
            </div>
          </div>
        )}

        <AlbumDetails
          album={selectedAlbum}
          isOpen={detailsOpen}
          onClose={handleCloseDetails}
        />
      </div>
    </div>
  );
}