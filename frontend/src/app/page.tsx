'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiClient, AlbumData, SearchResponse, FavoriteItem } from '@/lib/api';
import { useAuth } from './contexts/AuthContext';
import AlbumCard from './components/AlbumCard';
import SearchForm from './components/SearchForm';
import LoadingSpinner from './components/ui/LoadingSpinner';
import ErrorMessage from './components/ui/ErrorMessage';
import AuthModal from './components/auth/AuthModal';
import AlbumDetails from './components/AlbumDetails';
import Navigation from './components/Navigation';
import './page.css';


// This will be replaced by dynamic loading from Sessions database

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

  // Load initial albums and user favorites
  useEffect(() => {
    loadInitialAlbums();
    if (user) {
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
    setLoading(true);
    setError(null);
    
    const searchData: SearchResponse = await apiClient.searchAlbums(query);
    
    if (searchData.recommendations && searchData.recommendations.length > 0) {
      setAlbums(searchData.recommendations);
    } else {
      setAlbums([]);
      setError('No results found, try again later');
    }
    
  } catch (error) {
    console.error('Error searching albums:', error);
    setAlbums([]);
    setError('Bad connection, try again later');
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
        {/* Welcome Section */}
        <div className="welcome-section">
          <h1>Find your next favorite album</h1>
          <p>Discover deep cuts and hidden gems tailored to your unique taste</p>
        </div>

        {/* Search */}
        <SearchForm 
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
          onSubmit={handleSearchSubmit}
          loading={loading}
        />

        {/* Results Area */}
        {loading && <LoadingSpinner />}
        
        {error && <ErrorMessage error={error} />}
        
        {!loading && !error && albums.length > 0 && (
          <div className="albums-section">
            <h2 className="albums-title">{searchQuery ? `${albums.length} deep cut albums for ${searchQuery} lovers` : "Today's top favorites"}</h2>
            <div className="albums-grid">
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
        />
        </div>
      </div>
    </>
  );
}