'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient, AlbumData, SearchResponse } from '@/lib/api';
import { enrichAlbumWithSpotifyData, enrichAlbumsInParallel } from '@/lib/spotify';
import { useAuth } from './contexts/AuthContext';
import { useToast } from './contexts/ToastContext';
import AlbumCard from './components/AlbumCard';
import HeroHeader from './components/HeroHeader';
import ErrorMessage from './components/ui/ErrorMessage';
import AuthModal from './components/auth/AuthModal';
import AlbumDetails from './components/AlbumDetails';
import Navigation from './components/Navigation';
import SkeletonCard from './components/ui/SkeletonCard';
import './page.css';
import './components/RecommendationsSection.scss';

const MAX_CACHE_ENTRIES = 50;

/** Stable identity key for an album — matches by title+artist regardless of ID source */
const albumKey = (album: AlbumData) =>
  `${album.title?.toLowerCase().trim()}|${album.artist?.toLowerCase().trim()}`;

export default function Home() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [albums, setAlbums] = useState<AlbumData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedAlbum, setSelectedAlbum] = useState<AlbumData | null>(null);
  const [favoriteAlbums, setFavoriteAlbums] = useState<Set<string>>(new Set());
  const [favoriteIdMap, setFavoriteIdMap] = useState<Map<string, string>>(new Map());
  const favoritesLoadingRef = useRef(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

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
      setCurrentSessionId(searchData.session_id || null);
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
  if (!initialAlbums || initialAlbums.length === 0) return;

  await enrichAlbumsInParallel(initialAlbums, (original, enriched) => {
    setAlbums(current => current.map(a => a.id === original.id ? enriched : a));
    setSelectedAlbum(current => current?.id === original.id ? enriched : current);

    const key = albumKey(original);
    if (user && favoriteAlbums.has(key) && (enriched.spotify_url || enriched.discogs_url)) {
      const dbId = favoriteIdMap.get(key) || original.id;
      apiClient.updateFavorite(dbId, {
        spotify_url: enriched.spotify_url,
        spotify_preview_url: enriched.spotify_preview_url,
        discogs_url: enriched.discogs_url,
        cover_url: enriched.cover_url,
      }).catch(() => {});
    }
  });

  if (cacheKey && cacheKey.length > 0) {
    setAlbums(currentAlbums => {
      setSearchCache(prev => {
        const next = new Map(prev.set(cacheKey, currentAlbums));
        if (next.size > MAX_CACHE_ENTRIES) {
          const oldestKey = next.keys().next().value;
          if (oldestKey !== undefined) next.delete(oldestKey);
        }
        return next;
      });
      return currentAlbums;
    });
  }
};

const handleListenNow = async (album: AlbumData) => {
  setSelectedAlbum(album);
  setDetailsOpen(true);
  apiClient.trackClick(currentSessionId, album);

  if (!album.spotify_url && album.title && album.artist) {
    try {
      const enriched = await enrichAlbumWithSpotifyData(album);
      setSelectedAlbum(enriched);
      setAlbums(current => current.map(a => a.id === album.id ? enriched : a));

      const key = albumKey(album);
      if (user && favoriteAlbums.has(key) && (enriched.spotify_url || enriched.discogs_url)) {
        const dbId = favoriteIdMap.get(key) || album.id;
        apiClient.updateFavorite(dbId, {
          spotify_url: enriched.spotify_url,
          spotify_preview_url: enriched.spotify_preview_url,
          discogs_url: enriched.discogs_url,
          cover_url: enriched.cover_url,
        }).catch(() => {});
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
    if (!user || favoritesLoadingRef.current) return;
    
    try {
      favoritesLoadingRef.current = true;
      const response = await apiClient.getFavoritesWithDetails();
      
      if (response.success && response.favorites) {
        const keys = new Set<string>();
        const idMap = new Map<string, string>();
        for (const fav of response.favorites) {
          if (fav.album?.title && fav.album?.artist) {
            const key = albumKey(fav.album);
            keys.add(key);
            idMap.set(key, fav.album.id);
          }
        }
        setFavoriteAlbums(keys);
        setFavoriteIdMap(idMap);
      }
    } catch (error) {
      console.error('Error loading user favorites:', error);
    } finally {
      favoritesLoadingRef.current = false;
    }
  }, [user]);

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
    setFavoriteIdMap(new Map());
  }
}, [user, handleSearch, loadUserFavorites]);

const handleToggleFavorite = async (album: AlbumData) => {
  if (!user) {
    if (searchQuery) {
      sessionStorage.setItem('pendingSearchQuery', searchQuery);
    }
    setAuthModalOpen(true);
    return;
  }

  const key = albumKey(album);
  const isFavorited = favoriteAlbums.has(key);
  
  try {
    if (isFavorited) {
      const dbId = favoriteIdMap.get(key) || album.id;
      await apiClient.removeFromFavorites(dbId);
      setFavoriteAlbums(prev => {
        const newSet = new Set(prev);
        newSet.delete(key);
        return newSet;
      });
      setFavoriteIdMap(prev => {
        const newMap = new Map(prev);
        newMap.delete(key);
        return newMap;
      });
      showToast('Removed from favorites', 'success');
    } else {
      await apiClient.addToFavorites(album, undefined, currentSessionId ?? undefined);
      setFavoriteAlbums(prev => new Set(prev).add(key));
      showToast('Added to favorites', 'success');
    }
  } catch (error) {
    console.error('Error toggling favorite:', error);
    showToast('Failed to update favorites', 'error');
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
          <div className="recommendations-section">
            <p className="loading-hint-text" role="status" aria-live="polite">
              This may take 15-30 seconds for the best recommendations
            </p>
            <div className="recommendations-grid">
              {Array.from({ length: 6 }, (_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          </div>
        )}
        
        {error && <ErrorMessage error={error} onRetry={() => searchQuery ? handleSearch(searchQuery) : loadInitialAlbums()} />}
        
        {!loading && !error && albums.length > 0 && (
          <div className="recommendations-section">
            <h2 className="recommendations-title">{searchQuery ? `${albums.length} deep cut albums for ${searchQuery} lovers` : "Today's top favorites"}</h2>
            <div className="recommendations-grid">
              {albums.map((album, index) => (
                <AlbumCard 
                  key={album.id} 
                  album={album} 
                  index={index}
                  onListenNow={handleListenNow}
                  onToggleFavorite={handleToggleFavorite}
                  isFavorited={favoriteAlbums.has(albumKey(album))}
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