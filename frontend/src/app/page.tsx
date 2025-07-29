'use client';

import { useState, useEffect } from 'react';
import { apiClient, Album } from '@/lib/api';
import './page.css';

export default function Home() {

  const [albums, setAlbums] = useState<Album[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch albums
  useEffect(() => {
    
    async function fetchAlbums() {
      try {
        setLoading(true);     
        setError(null);     
        
        const albumData = await apiClient.getAlbums();
        console.log('Received album data:', albumData);
        console.log('Is array:', Array.isArray(albumData));
        
        if (Array.isArray(albumData)) {
          setAlbums(albumData); 
        } else {
          throw new Error('Invalid data format received from API');
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

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-content">
          <div className="loading-spinner"></div>
          <p className="loading-text">Loading...</p>
        </div>
      </div>
    );
  }

  if (error) {

    return (
      <div className="error-container">
        <div className="error-content">
          <p className="error-message">{error}</p>
          <p className="error-description">Something went wrong :/</p>
        </div>
      </div>
    );
  }

  // Albums
  return (
    <div className="page-container">
      <div className="container">
        
        {/* Header Section */}
        <header className="header">
          <h1>DeepCuts</h1>
          <p>Album Discovery</p>
        </header>

        {/* Albums Display */}
        <div className="albums-section">
          <h2 className="albums-title">Albums ({albums.length})</h2>
          
          {/* Album Grid */}
          <div className="albums-grid">
            {albums && Array.isArray(albums) && albums.map((album) => (
              //album
              <div key={album.id} className="album-card">
                <h3 className="album-title">{album.title || 'Unknown Title'}</h3>
                <p className="album-artist">{album.artist || 'Unknown Artist'}</p>
                <p className="album-year">{album.release_year || 'Unknown Year'}</p>
                {album.genre && <p className="album-genre">{album.genre}</p>}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}