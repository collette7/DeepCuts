'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient, AlbumData, FavoriteItem } from '@/lib/api';
import { enrichAlbumsInParallel } from '@/lib/spotify';
import AlbumCard from '../components/AlbumCard';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorMessage from '../components/ui/ErrorMessage';
import AlbumDetails from '../components/AlbumDetails';
import Navigation from '../components/Navigation';
import '../components/RecommendationsSection.scss';
import './page.scss';


export default function FavoritesPage() {
  const { user, loading: authLoading } = useAuth();
  const { showToast } = useToast();
  const router = useRouter();
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlbum, setSelectedAlbum] = useState<AlbumData | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [removingIds, setRemovingIds] = useState<Set<string>>(new Set());

  const loadSpotifyDataForFavorites = useCallback(async (albums: AlbumData[]) => {
    await enrichAlbumsInParallel(albums, (original, enriched) => {
      setFavorites(current =>
        current.map(fav =>
          fav.album?.id === original.id ? { ...fav, album: enriched } : fav
        )
      );
      setSelectedAlbum(current => current?.id === original.id ? enriched : current);
    });
  }, []);

  const loadFavorites = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.getFavoritesWithDetails();
      
      // Handle specific error cases
      if (response.error === 'Network error') {
        setError('Unable to connect to server. Please check your internet connection.');
        return;
      }
      if (response.error === 'Request timeout') {
        setError('Request timed out. The server may be slow. Please try again.');
        return;
      }
      
      if (response.favorites) {
        // Convert favorites to albums array for enrichment
        const albums = response.favorites
          .map(fav => fav.album)
          .filter((album): album is AlbumData => album !== undefined);
        
        setFavorites(response.favorites);
        setLoading(false);
        
        // Now load Spotify data progressively in the background
        if (albums.length > 0) {
          loadSpotifyDataForFavorites(albums);
        }
      } else {
        setFavorites([]);
        setLoading(false);
      }
    } catch (error) {
      console.error('Error loading favorites:', error);
      setError('Failed to load your favorites. Please try again.');
      setLoading(false);
    }
  }, [loadSpotifyDataForFavorites]);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    
    if (user) {
      loadFavorites();
    } else {
      router.push('/');
    }
  }, [user, authLoading, router, loadFavorites]);

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
      setFavorites(prev => prev.filter(fav => fav.album?.id !== album.id));
      showToast('Removed from favorites', 'success');
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

  if (authLoading || loading) {
    return (
      <>
        <Navigation />
        <div className="page-container">
          <div className="container loading-center">
            <LoadingSpinner />
          </div>
        </div>
      </>
    );
  }

  if (!user) return null;


  return (
    <>
      <Navigation />
      <div className="page-container">
        <div className="container">
        <header className="header">
          <div>
            <h1>favorites</h1>
            <p>{favorites.length} albums saved</p>
          </div>
        </header>

        {error && <ErrorMessage error={error} onRetry={loadFavorites} />}

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
          <div className="recommendations-section">
            <div className="recommendations-grid">
              {favorites.map((favorite, index) => {
                const album = favorite.album;
                
                if (!album) return null;
                
                const albumWithReasoning = {
                  ...album,
                  reasoning: favorite.reasoning || album.reasoning
                };
                
                return (
                  <AlbumCard 
                    key={favorite.id || album.id}
                    album={albumWithReasoning}
                    index={index}
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
          user={user}
          hiderecommendationReason={false}
          onAuthRequired={() => {
            // Favorites page already requires login, but just in case
            router.push('/');
          }}
        />
        </div>
      </div>
    </>
  );
}