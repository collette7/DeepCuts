'use client';

import { useState, useEffect } from 'react';
import { apiClient, AlbumData, SearchResponse } from '@/lib/api';
import AlbumCard from './components/AlbumCard';
import SearchForm from './components/SearchForm';
import LoadingSpinner from './components/ui/LoadingSpinner';
import ErrorMessage from './components/ui/ErrorMessage';
import './page.css';

export default function Home() {

  const [albums, setAlbums] = useState<AlbumData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState('Miles Davis');

const handleSearch = async (e: React.FormEvent) => {
  e.preventDefault();
  
  try {
    setLoading(true);
    setError(null);
    
    const searchData: SearchResponse = await apiClient.searchAlbums(searchQuery);
    setAlbums(searchData.recommendations);
    
  } catch (error) {
    console.error('Error searching albums:', error);
    setError(error instanceof Error ? error.message : 'Search failed');
  } finally {
    setLoading(false);
  }
};

  // Fetch albums
  useEffect(() => {
    
    async function fetchAlbums() {
      try {
        setLoading(true);     
        setError(null);     
        
        const searchData: SearchResponse = await apiClient.searchAlbums();
        console.log('Search data:', searchData);
        console.log('Is array:', Array.isArray(searchData.recommendations));
        
        if (searchData && searchData.recommendations && Array.isArray(searchData.recommendations)) {
          setAlbums(searchData.recommendations); 
        } else {
          throw new Error('Bad data format');
        }
        
      } catch (err) {
        console.error('Error in fetchAlbums:', err);
        setError(err instanceof Error ? err.message : 'Something went wrong');
        
      } finally {
        setLoading(false);  
      }
    }

    fetchAlbums();
  }, []);


  // Albums
  return (
    <div className="page-container">
      <div className="container">
        
        {/* Header */}
        <header className="header">
          <h1>DeepCuts</h1>
          <p>Album Discovery</p>
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
            <h2 className="albums-title">Recommended Albums ({albums.length})</h2>
            <div className="albums-grid">
              {albums.map((album) => (
                <AlbumCard key={album.id} album={album} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}