'use client';

import { useState, useEffect } from 'react';
import { apiClient, AlbumData, SearchResponse } from '@/lib/api';
import { useAuth } from './contexts/AuthContext';
import AlbumCard from './components/AlbumCard';
import SearchForm from './components/SearchForm';
import LoadingSpinner from './components/ui/LoadingSpinner';
import ErrorMessage from './components/ui/ErrorMessage';
import AuthModal from './components/auth/AuthModal';
import AlbumDetails from './components/AlbumDetails';
import './page.css';

// Example search results
const exampleSearchResults: AlbumData[] = [
  {
    id: '1',
    title: 'Live-Evil',
    artist: 'Miles Davis',
    year: 1971,
    genre: 'Electric Jazz'
  },
  {
    id: '2',
    title: 'I Sing the Body Electric',
    artist: 'Weather Report',
    year: 1972,
    genre: 'Jazz Fusion'
  },
  {
    id: '3',
    title: 'Emergency!',
    artist: 'Tony Williams Lifetime',
    year: 1969,
    genre: 'Jazz Rock'
  },
  {
    id: '4',
    title: 'Mwandishi',
    artist: 'Herbie Hancock',
    year: 1971,
    genre: 'Electric Jazz'
  },
  {
    id: '5',
    title: 'Turn It Over',
    artist: 'Tony Williams Lifetime',
    year: 1970,
    genre: 'Jazz Rock'
  },
  {
    id: '6',
    title: 'Crossings',
    artist: 'Herbie Hancock',
    year: 1972,
    genre: 'Electric Jazz'
  },
  {
    id: '7',
    title: 'The Inner Mounting Flame',
    artist: 'Mahavishnu Orchestra',
    year: 1971,
    genre: 'Jazz Fusion'
  },
  {
    id: '8',
    title: 'Third',
    artist: 'Soft Machine',
    year: 1970,
    genre: 'Canterbury Scene'
  },
  {
    id: '9',
    title: 'Waka/Jawaka',
    artist: 'Frank Zappa',
    year: 1972,
    genre: 'Jazz Rock'
  },
  {
    id: '10',
    title: 'Lawrence of Newark',
    artist: 'Larry Young',
    year: 1973,
    genre: 'Electric Jazz'
  }
];

export default function Home() {
  const { user, signOut } = useAuth();
  const [albums, setAlbums] = useState<AlbumData[]>(exampleSearchResults);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedAlbum, setSelectedAlbum] = useState<AlbumData | null>(null);
  const [favoriteAlbums, setFavoriteAlbums] = useState<Set<string>>(new Set());
  const [sourceAlbum, setSourceAlbum] = useState<AlbumData | null>(null);
  const [favoritesLoading, setFavoritesLoading] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');

  // Load user favorites when user changes
  useEffect(() => {
    if (user) {
      loadUserFavorites();
    } else {
      setFavoriteAlbums(new Set());
    }
  }, [user]);

const handleSearch = async (e: React.FormEvent) => {
  e.preventDefault();
  
  try {
    setLoading(true);
    setError(null);
    
    const searchData: SearchResponse = await apiClient.searchAlbums(searchQuery);
    
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

const loadUserFavorites = async () => {
  if (!user || favoritesLoading) return;
  
  try {
    setFavoritesLoading(true);
    const response = await apiClient.getFavoritesWithDetails();
    
    if (response.success && response.favorites) {
      // Extract album IDs from the favorites response
      const favoriteIds = new Set(response.favorites.map((fav: any) => fav.album?.id || fav.id).filter(Boolean));
      setFavoriteAlbums(favoriteIds);
    }
  } catch (error) {
    console.error('Error loading user favorites:', error);
  } finally {
    setFavoritesLoading(false);
  }
};

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
      await apiClient.addToFavorites(album, sourceAlbum);
      setFavoriteAlbums(prev => new Set(prev).add(album.id));
    }
  } catch (error) {
    console.error('Error toggling favorite:', error);
    // Could show a toast notification here
  }
};



  // Albums
  return (
    <div className="page-container">
      <div className="container">
        
        {/* Header */}
        <header className="header">
          <div>
            <h1>DeepCuts</h1>
            <p>Album Discovery</p>
          </div>
          <div className="auth-controls">
            {user ? (
              <div className="user-menu">
                <span>Welcome, {user.email}</span>
                <button onClick={signOut}>Sign Out</button>
              </div>
            ) : (
              <div className="auth-buttons">
                <button onClick={() => setAuthModalOpen(true)}>Sign In</button>
              </div>
            )}
          </div>
        </header>

        {/* Search */}
        <SearchForm 
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
          onSubmit={handleSearch}
          loading={loading}
        />

        {/* Results Area */}
        {loading && <LoadingSpinner />}
        
        {error && <ErrorMessage error={error} />}
        
        {!loading && !error && albums.length > 0 && (
          <div className="albums-section">
            <h2 className="albums-title">{albums.length} deep cut albums for {searchQuery || 'music'} lovers</h2>
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
  );
}