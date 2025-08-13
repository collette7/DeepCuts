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
import './page.scss';


export default function FavoritesPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [favorites, setFavorites] = useState<FavoriteItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlbum, setSelectedAlbum] = useState<AlbumData | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [removingIds, setRemovingIds] = useState<Set<string>>(new Set());

  const loadSpotifyDataForFavorites = useCallback(async (albums: AlbumData[]) => {
    // Load Spotify data for each album in parallel
    const promises = albums.map(async (album) => {
      try {
        const spotifyData = await apiClient.getAlbumSpotifyData(album.id, album.title, album.artist);
        
        // Update the favorites state with enriched album data
        setFavorites(currentFavorites => 
          currentFavorites.map(fav => {
            const favAlbum = fav.albums || fav.album;
            if (favAlbum && favAlbum.id === album.id) {
              const enrichedAlbum = {
                ...favAlbum,
                spotify_preview_url: spotifyData.spotify_preview_url,
                spotify_url: spotifyData.spotify_url,
                cover_url: spotifyData.cover_url || favAlbum.cover_url,
                discogs_url: spotifyData.discogs_url || favAlbum.discogs_url
              };
              
              // Update the favorite with the enriched album
              return {
                ...fav,
                albums: fav.albums ? enrichedAlbum : fav.albums,
                album: fav.album ? enrichedAlbum : fav.album
              };
            }
            return fav;
          })
        );
        
        // Also update selected album if it's currently being viewed
        setSelectedAlbum(current => 
          current && current.id === album.id 
            ? {
                ...current,
                spotify_preview_url: spotifyData.spotify_preview_url,
                spotify_url: spotifyData.spotify_url,
                cover_url: spotifyData.cover_url || current.cover_url,
                discogs_url: spotifyData.discogs_url || current.discogs_url
              }
            : current
        );
      } catch (error) {
        console.error(`Failed to load Spotify data for ${album.title}:`, error);
      }
    });
    
    // Wait for all to complete
    await Promise.all(promises);
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
          .map(fav => fav.albums || fav.album)
          .filter(Boolean);
        
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
          <div className="container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
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