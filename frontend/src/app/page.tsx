'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient, AlbumData, SearchResponse, FavoriteItem } from '@/lib/api';
import { useAuth } from './contexts/AuthContext';
import AlbumCard from './components/AlbumCard';
import HeroHeader from './components/HeroHeader';
import ErrorMessage from './components/ui/ErrorMessage';
import AuthModal from './components/auth/AuthModal';
import AlbumDetails from './components/AlbumDetails';
import Navigation from './components/Navigation';
import './page.css';
import './components/RecommendationsSection.scss';


// Dynamic loading from Sessions database

export default function Home() {
  const { user } = useAuth();
  const [albums, setAlbums] = useState<AlbumData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedAlbum, setSelectedAlbum] = useState<AlbumData | null>(null);
  const [favoriteAlbums, setFavoriteAlbums] = useState<Set<string>>(new Set());
  const [favoritesLoading, setFavoritesLoading] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchCache, setSearchCache] = useState<Map<string, AlbumData[]>>(new Map());
  const [initialLoadDone, setInitialLoadDone] = useState(false);

  const loadInitialAlbums = useCallback(async () => {
    try {
      setLoading(true);
      const response = await apiClient.getRandomAlbums(10);
      setAlbums(response.albums);
      
      // Load Spotify data for initial albums in the background
      if (response.albums && response.albums.length > 0) {
        loadSpotifyDataProgressively(response.albums, 'initial-load');
      }
    } catch (error) {
      console.error('Error loading initial albums:', error);
      setError('Failed to load albums');
    } finally {
      setLoading(false);
    }
  }, []);

const handleSearchSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  await handleSearch(searchQuery);
};

const handleSearch = useCallback(async (query: string) => {
  try {
    setSearchQuery(query);
    setError(null);
    
    // Check cache first
    const cacheKey = query.toLowerCase().trim();
    if (searchCache.has(cacheKey)) {
      setAlbums(searchCache.get(cacheKey) || []);
      return;
    }
    
    setLoading(true);
    
    const searchData: SearchResponse = await apiClient.searchAlbums(query);
    
    if (searchData.recommendations && searchData.recommendations.length > 0) {
      // Show AI results immediately
      setAlbums(searchData.recommendations);
      setLoading(false);
      
      // Now load Spotify data progressively in the background
      loadSpotifyDataProgressively(searchData.recommendations, cacheKey);
    } else {
      setAlbums([]);
      setError('No results found, try again later');
      setLoading(false);
    }
    
  } catch (error) {
    console.error('Error searching albums:', error);
    setAlbums([]);
    // More specific error handling
    if (error instanceof TypeError && error.message === 'Failed to fetch') {
      setError('Connection error. Please check your internet connection.');
    } else {
      setError('Bad connection, try again later');
    }
    setLoading(false);
  }
}, [searchCache]);

const loadSpotifyDataProgressively = async (initialAlbums: AlbumData[], cacheKey: string) => {
  // Ensure we're working with valid data
  if (!initialAlbums || initialAlbums.length === 0) return;
  
  // Load Spotify data for each album in parallel
  const promises = initialAlbums.map(async (album) => {
    try {
      // Skip if album data is invalid
      if (!album || !album.id || !album.title || !album.artist) {
        console.warn('Invalid album data:', album);
        return;
      }
      
      const spotifyData = await apiClient.getAlbumSpotifyData(album.id, album.title, album.artist);
      
      const enrichedAlbum = {
        ...album,
        spotify_preview_url: spotifyData.spotify_preview_url,
        spotify_url: spotifyData.spotify_url,
        cover_url: spotifyData.cover_url || album.cover_url,
        discogs_url: spotifyData.discogs_url || album.discogs_url
      };
      
      // Update this specific album with Spotify and Discogs data
      setAlbums(currentAlbums => 
        currentAlbums.map(a => 
          a.id === album.id ? enrichedAlbum : a
        )
      );
      
      // Also update selected album if it's currently being viewed
      setSelectedAlbum(current => 
        current && current.id === album.id ? enrichedAlbum : current
      );
      
      // If this album is favorited and we got new data, update the favorite (non-blocking)
      if (user && favoriteAlbums.has(album.id) && (spotifyData.spotify_url || spotifyData.discogs_url)) {
        apiClient.updateFavorite(album.id, {
          spotify_url: spotifyData.spotify_url,
          spotify_preview_url: spotifyData.spotify_preview_url,
          discogs_url: spotifyData.discogs_url,
          cover_url: spotifyData.cover_url
        }).catch(() => {
          // Silently handle update failures - not critical
        });
      }
    } catch (error) {
      console.error(`Failed to load Spotify data for ${album?.title}:`, error);
    }
  });
  
  // Wait for all to complete, then cache the final results
  await Promise.all(promises);
  
  // Update cache with enriched results (only if cacheKey is valid)
  if (cacheKey && cacheKey.length > 0) {
    setAlbums(currentAlbums => {
      setSearchCache(prev => new Map(prev.set(cacheKey, currentAlbums)));
      return currentAlbums;
    });
  }
};

const handleListenNow = async (album: AlbumData) => {
  // Open the details immediately
  setSelectedAlbum(album);
  setDetailsOpen(true);
  
  // If no Spotify URL, try to fetch it in the background
  if (!album.spotify_url && album.title && album.artist) {
    try {
      const spotifyData = await apiClient.getAlbumSpotifyData(album.id, album.title, album.artist);
      const enrichedAlbum = {
        ...album,
        spotify_url: spotifyData.spotify_url,
        spotify_preview_url: spotifyData.spotify_preview_url,
        cover_url: spotifyData.cover_url || album.cover_url,
        discogs_url: spotifyData.discogs_url || album.discogs_url
      };
      setSelectedAlbum(enrichedAlbum);
      
      // Also update the album in the main list
      setAlbums(current => 
        current.map(a => a.id === album.id ? enrichedAlbum : a)
      );
      
      // If this album is favorited and we got new data, update the favorite (non-blocking)
      if (user && favoriteAlbums.has(album.id) && (spotifyData.spotify_url || spotifyData.discogs_url)) {
        apiClient.updateFavorite(album.id, {
          spotify_url: spotifyData.spotify_url,
          spotify_preview_url: spotifyData.spotify_preview_url,
          discogs_url: spotifyData.discogs_url,
          cover_url: spotifyData.cover_url
        }).catch(() => {
          // Silently handle update failures - not critical
        });
      }
    } catch (error) {
      console.error('Failed to fetch Spotify data for album:', error);
    }
  }
};

const handleCloseDetails = () => {
  setDetailsOpen(false);
  setSelectedAlbum(null);
};

const loadUserFavorites = useCallback(async () => {
  if (!user || favoritesLoading) return;
  
  try {
    setFavoritesLoading(true);
    const response = await apiClient.getFavoritesWithDetails();
    
    if (response.success && response.favorites) {
      // Extract album IDs from the favorites response
      const favoriteIds = new Set(response.favorites.map((fav: FavoriteItem) => fav.albums?.id || fav.album?.id || fav.id).filter(Boolean));
      setFavoriteAlbums(favoriteIds);
    }
  } catch (error) {
    console.error('Error loading user favorites:', error);
  } finally {
    setFavoritesLoading(false);
  }
}, [user, favoritesLoading]);

// Initial load on mount
useEffect(() => {
  if (!initialLoadDone && !searchQuery) {
    loadInitialAlbums();
    setInitialLoadDone(true);
  }
}, [initialLoadDone, searchQuery, loadInitialAlbums]);

// Handle user auth changes
useEffect(() => {
  if (user) {
    // Check for pending search query after login
    const pendingQuery = sessionStorage.getItem('pendingSearchQuery');
    if (pendingQuery) {
      // Small delay to ensure auth state is fully established
      setTimeout(() => {
        sessionStorage.removeItem('pendingSearchQuery');
        // Restore the search query visually first
        setSearchQuery(pendingQuery);
        // Then execute the search
        handleSearch(pendingQuery);
      }, 100);
    }
    loadUserFavorites();
  } else {
    setFavoriteAlbums(new Set());
  }
}, [user, handleSearch, loadUserFavorites]);

const handleToggleFavorite = async (album: AlbumData) => {
  if (!user) {
    // Store current search query in sessionStorage before opening auth modal
    if (searchQuery) {
      sessionStorage.setItem('pendingSearchQuery', searchQuery);
    }
    setAuthModalOpen(true);
    return;
  }

  const isFavorited = favoriteAlbums.has(album.id);
  
  try {
    if (isFavorited) {
      await apiClient.removeFromFavorites(album.id);
      setFavoriteAlbums(prev => {
        const newSet = new Set(prev);
        newSet.delete(album.id);
        return newSet;
      });
    } else {
      await apiClient.addToFavorites(album);
      setFavoriteAlbums(prev => new Set(prev).add(album.id));
    }
  } catch (error) {
    console.error('Error toggling favorite:', error);
    // Could show a toast notification here
  }
};



  // Albums
  return (
    <>
      <Navigation />
      <div className="page-container">
        <div className="container">
          {/* Hero Header with Search */}
          <HeroHeader 
            searchQuery={searchQuery}
            onSearchQueryChange={setSearchQuery}
            onSubmit={handleSearchSubmit}
            loading={loading}
          />

        {/* Results Area */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <p style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: '#999' }}>
              This may take 15-30 seconds for the best recommendations
            </p>
          </div>
        )}
        
        {error && <ErrorMessage error={error} />}
        
        {!loading && !error && albums.length > 0 && (
          <div className="recommendations-section">
            <h2 className="recommendations-title">{searchQuery ? `${albums.length} deep cut albums for ${searchQuery} lovers` : "Today's top favorites"}</h2>
            <div className="recommendations-grid">
              {albums.map((album) => (
                <AlbumCard 
                  key={album.id} 
                  album={album} 
                  onListenNow={handleListenNow}
                  onToggleFavorite={handleToggleFavorite}
                  isFavorited={favoriteAlbums.has(album.id)}
                />
              ))}
            </div>
          </div>
        )}

        <AuthModal 
          isOpen={authModalOpen} 
          onClose={() => setAuthModalOpen(false)} 
        />

        <AlbumDetails
          album={selectedAlbum}
          isOpen={detailsOpen}
          onClose={handleCloseDetails}
          user={user}
          onAuthRequired={() => {
            handleCloseDetails();
            // Store current search query in sessionStorage before opening auth modal
            if (searchQuery) {
              sessionStorage.setItem('pendingSearchQuery', searchQuery);
            }
            setAuthModalOpen(true);
          }}
        />
        </div>
      </div>
    </>
  );
}