'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';
import { apiClient, AlbumData, FavoriteItem } from '@/lib/api';
import AlbumCard from '../components/AlbumCard';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorMessage from '../components/ui/ErrorMessage';
import AlbumDetails from '../components/AlbumDetails';
import Navigation from '../components/Navigation';
import '../components/RecommendationsSection.scss';


export default function FavoritesPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlbum, setSelectedAlbum] = useState<AlbumData | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [removingIds, setRemovingIds] = useState<Set<string>>(new Set());
  const [fetchingSpotifyData, setFetchingSpotifyData] = useState(false);

  const loadFavorites = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.getFavoritesWithDetails();
      
      console.log('Favorites response:', response);
      
      if (response.favorites) {
        console.log('First favorite album data:', response.favorites[0]);
        setFavorites(response.favorites);
      } else {
        // Empty favorites is not an error, just set empty array
        setFavorites([]);
      }
    } catch (error) {
      console.error('Error loading favorites:', error);
      setError('Failed to load your favorites. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) {
      // Still loading auth state, don't do anything yet
      return;
    }
    
    if (user) {
      loadFavorites();
    } else {
      // User is not authenticated, redirect to home
      router.push('/');
    }
  }, [user, authLoading, router, loadFavorites]);

  const handleListenNow = async (album: AlbumData) => {
    console.log('Selected album for details:', album);
    console.log('Album has spotify_url:', album.spotify_url);
    
    // Open the details immediately with what we have
    setSelectedAlbum(album);
    setDetailsOpen(true);
    
    // If no Spotify URL, try to fetch it in the background
    if (!album.spotify_url && album.title && album.artist) {
      setFetchingSpotifyData(true);
      try {
        const spotifyData = await apiClient.getAlbumSpotifyData(album.id, album.title, album.artist);
        const enrichedAlbum = {
          ...album,
          spotify_url: spotifyData.spotify_url,
          spotify_preview_url: spotifyData.spotify_preview_url,
          cover_url: spotifyData.cover_url || album.cover_url
        };
        setSelectedAlbum(enrichedAlbum);
        
        // Also update the album in the favorites list
        setFavorites(prev => prev.map(fav => {
          const favAlbum = fav.albums || fav.album;
          if (favAlbum?.id === album.id) {
            return {
              ...fav,
              albums: enrichedAlbum,
              album: enrichedAlbum
            };
          }
          return fav;
        }));
      } catch (error) {
        console.error('Failed to fetch Spotify data:', error);
      } finally {
        setFetchingSpotifyData(false);
      }
    }
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

  if (authLoading || loading) {
    return (
      <>
        <Navigation />
        <div className="page-container">
          <div className="container">
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
            <h1>Your Favorites</h1>
            <p>{favorites.length} albums saved</p>
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
          <div className="recommendations-section">
            <div className="recommendations-grid">
              {favorites.map((favorite) => {
                // Handle different response formats
                const album = favorite.albums || favorite.album;
                
                if (!album) return null; // Skip if no album data
                
                // Merge reasoning from favorites record into album data (if available)
                const albumWithReasoning = {
                  ...album,
                  reasoning: favorite?.reasoning || album?.reasoning
                };
                
                return (
                  <AlbumCard 
                    key={favorite.id || album.id}
                    album={albumWithReasoning}
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
          hiderecommendationReason={true}
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