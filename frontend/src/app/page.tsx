'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient, AlbumData, SearchResponse, FavoriteItem } from '@/lib/api';
import { useAuth } from './contexts/AuthContext';
import AlbumCard from './components/AlbumCard';
import HeroHeader from './components/HeroHeader';
import LoadingSpinner from './components/ui/LoadingSpinner';
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
  const [loadingMessage, setLoadingMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedAlbum, setSelectedAlbum] = useState<AlbumData | null>(null);
  const [favoriteAlbums, setFavoriteAlbums] = useState<Set<string>>(new Set());
  const [favoritesLoading, setFavoritesLoading] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchCache, setSearchCache] = useState<Map<string, AlbumData[]>>(new Map());
  const [initialLoadDone, setInitialLoadDone] = useState(false);

  // Initial load on mount
  useEffect(() => {
    if (!initialLoadDone && !searchQuery) {
      loadInitialAlbums();
      setInitialLoadDone(true);
    }
  }, []);

  // Handle user auth changes
  useEffect(() => {
    if (user) {
      // Check for pending search query after login
      const pendingQuery = sessionStorage.getItem('pendingSearchQuery');
      if (pendingQuery) {
        sessionStorage.removeItem('pendingSearchQuery');
        handleSearch(pendingQuery);
      }
      loadUserFavorites();
    } else {
      setFavoriteAlbums(new Set());
    }
  }, [user]);

  const loadInitialAlbums = async () => {
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
  };

const handleSearchSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  await handleSearch(searchQuery);
};

const handleSearch = async (query: string) => {
  try {
    setSearchQuery(query);
    setError(null);
    
    // Check cache first
    const cacheKey = query.toLowerCase().trim();
    if (searchCache.has(cacheKey)) {
      console.log('Using cached results for:', query);
      setAlbums(searchCache.get(cacheKey) || []);
      return;
    }
    
    setLoading(true);
    //setLoadingMessage('Searching for deep cuts...');
    
    const searchData: SearchResponse = await apiClient.searchAlbums(query);
    
    if (searchData.recommendations && searchData.recommendations.length > 0) {
      // Show AI results immediately
      setAlbums(searchData.recommendations);
      setLoading(false);
      setLoadingMessage('');
      
      // Now load Spotify data progressively in the background
      loadSpotifyDataProgressively(searchData.recommendations, cacheKey);
    } else {
      setAlbums([]);
      setError('No results found, try again later');
      setLoading(false);
      setLoadingMessage('');
    }
    
  } catch (error) {
    console.error('Error searching albums:', error);
    setAlbums([]);
    setError('Bad connection, try again later');
    setLoading(false);
    setLoadingMessage('');
  }
};

const loadSpotifyDataProgressively = async (initialAlbums: AlbumData[], cacheKey: string) => {
  console.log('Loading Spotify data for', initialAlbums.length, 'albums...');
  
  // Load Spotify data for each album in parallel
  const promises = initialAlbums.map(async (album, index) => {
    try {
      const spotifyData = await apiClient.getAlbumSpotifyData(album.id, album.title, album.artist);
      
      // Update this specific album with Spotify and Discogs data
      setAlbums(currentAlbums => 
        currentAlbums.map(a => 
          a.id === album.id 
            ? {
                ...a,
                spotify_preview_url: spotifyData.spotify_preview_url,
                spotify_url: spotifyData.spotify_url,
                cover_url: spotifyData.cover_url || a.cover_url,
                discogs_url: spotifyData.discogs_url || a.discogs_url
              }
            : a
        )
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
  
  // Wait for all to complete, then cache the final results
  await Promise.all(promises);
  
  // Update cache with enriched results
  setAlbums(currentAlbums => {
    setSearchCache(prev => new Map(prev.set(cacheKey, currentAlbums)));
    return currentAlbums;
  });
  
  console.log('Finished loading Spotify data progressively');
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