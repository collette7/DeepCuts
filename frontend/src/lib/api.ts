import { handleAuthError, isRefreshTokenError } from './auth-error-handler';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

class ApiClient {
    // client for FastAPI 
    // source of truth for all comms with backend

    private async getAuthHeaders(): Promise<HeadersInit> {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json'
        };

        try {
            const { supabase } = await import('@/lib/supabase');
            const { data: { session }, error } = await supabase.auth.getSession();
            
            if (error) {
                console.warn('Auth session error:', error);
                
                // Handle refresh token errors
                if (isRefreshTokenError(error)) {
                    await handleAuthError(error);
                }
                
                return headers;
            }
            
            if (session?.access_token) {
                headers['Authorization'] = `Bearer ${session.access_token}`;
            }
        } catch (error) {
            console.error('Error getting auth headers:', error);
            
            // Handle refresh token errors
            if (isRefreshTokenError(error)) {
                await handleAuthError(error);
            }
        }
        
        return headers;
    }

    async getWelcome() {
        //Get welcome message
        const response = await fetch(`${API_BASE_URL}/`);
        return response.json();
    }
    async searchAlbums(query: string = 'Miles Davis') {
        //Search albums
        try {
            // Sanitize query input
            const sanitizedQuery = query.trim().slice(0, 200); // Limit length and trim
            if (!sanitizedQuery) {
                throw new Error('Query cannot be empty');
            }
            
            const response = await fetch(`${API_BASE_URL}/api/v1/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: sanitizedQuery })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    async searchDiscogs(query: string) {
        //Search Discogs for autocomplete
        try {
            // Sanitize query input
            const sanitizedQuery = query.trim().slice(0, 200);
            if (!sanitizedQuery) {
                throw new Error('Query cannot be empty');
            }
            
            const response = await fetch(`${API_BASE_URL}/api/v1/discogs/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    query: sanitizedQuery,
                    type: 'release',
                    per_page: 10 
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Discogs API Error:', error);
            throw error;
        }
    }

    async addToFavorites(albumData: AlbumData, sourceAlbumData?: AlbumData): Promise<FavoriteActionResponse> {
        if (!albumData || !albumData.id) {
            throw new Error('Album data is required');
        }

        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/favorites/add`, {
                method: 'POST',
                headers: await this.getAuthHeaders(),
                body: JSON.stringify({ 
                    album_data: albumData,
                    source_album_data: sourceAlbumData 
                })
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Please sign in to save favorites');
                }
                const errorData = await response.json().catch(() => null);
                throw new Error(errorData?.detail || `Failed to add favorite (${response.status})`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Add to favorites error:', error);
            throw error;
        }
    }

    async removeFromFavorites(albumId: string): Promise<FavoriteActionResponse> {
        try {
            // Sanitize albumId to prevent path traversal
            const sanitizedAlbumId = encodeURIComponent(albumId);
            const response = await fetch(`${API_BASE_URL}/api/v1/favorites/remove/${sanitizedAlbumId}`, {
                method: 'DELETE',
                headers: await this.getAuthHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Remove from favorites error:', error);
            throw error;
        }
    }

    async updateFavorite(albumId: string, albumData: Partial<AlbumData>): Promise<FavoriteActionResponse> {
        try {
            // Sanitize albumId to prevent path traversal
            const sanitizedAlbumId = encodeURIComponent(albumId);
            const response = await fetch(`${API_BASE_URL}/api/v1/favorites/update/${sanitizedAlbumId}`, {
                method: 'PATCH',
                headers: await this.getAuthHeaders(),
                body: JSON.stringify({ album_data: albumData })
            });

            if (!response.ok) {
                if (response.status === 404) {
                    // Album not in favorites, ignore silently
                    return { success: false, message: 'Album not in favorites' };
                }
                if (response.status === 405) {
                    // Method not allowed - endpoint doesn't exist yet, ignore silently
                    return { success: false, message: 'Update endpoint not available' };
                }
                return { success: false, message: `Update failed: ${response.status}` };
            }
            
            return await response.json();
        } catch (error) {
            // Silently handle network errors for non-critical update operations
            return { success: false, message: 'Update failed' };
        }
    }

    async getFavoritesWithDetails(): Promise<FavoritesWithDetailsResponse> {
        try {
            const headers = await this.getAuthHeaders();
            
            // Add timeout to prevent hanging requests
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000);
            
            const response = await fetch(`${API_BASE_URL}/api/v1/favorites/with-details`, {
                method: 'GET',
                headers: headers,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                if (response.status === 401) {
                    return { success: false, favorites: [], total: 0 };
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            // Handle different types of errors
            if (error instanceof Error) {
                if (error.name === 'AbortError') {
                    return { success: false, favorites: [], total: 0, error: 'Request timeout' };
                }
                if (error.message === 'Failed to fetch') {
                    return { success: false, favorites: [], total: 0, error: 'Network error' };
                }
            }
            console.error('Get favorites with details error:', error);
            return { success: false, favorites: [], total: 0 };
        }
    }

    async getRandomAlbums(limit: number = 10): Promise<{albums: AlbumData[], total: number}> {
        try {
            // Sanitize and validate limit parameter
            const sanitizedLimit = Math.max(1, Math.min(100, Math.floor(limit)));
            
            // Add timeout to prevent hanging requests
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000);
            
            const response = await fetch(`${API_BASE_URL}/api/v1/albums/random?limit=${sanitizedLimit}`, {
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            // Handle different types of errors gracefully
            if (error instanceof Error) {
                if (error.name === 'AbortError') {
                    console.warn('Random albums request timed out');
                    return { albums: [], total: 0 };
                }
                if (error.message === 'Failed to fetch') {
                    console.warn('Failed to connect to backend server');
                    return { albums: [], total: 0 };
                }
            }
            console.error('Get random albums error:', error);
            return { albums: [], total: 0 };
        }
    }

    async getAlbumSpotifyData(albumId: string, title: string, artist: string): Promise<{
        album_id: string;
        spotify_preview_url?: string;
        spotify_url?: string;
        cover_url?: string;
        discogs_url?: string;
    }> {
        try {
            // Sanitize albumId to prevent path traversal
            const sanitizedAlbumId = encodeURIComponent(albumId);
            const params = new URLSearchParams({
                title: title,
                artist: artist
            });
            
            const response = await fetch(`${API_BASE_URL}/api/v1/albums/${sanitizedAlbumId}/spotify?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Get album Spotify data error:', error);
            throw error;
        }
    }


}

export const apiClient = new ApiClient();

export interface AlbumData {
    id: string;
    title: string;
    artist: string;
    year?: number;
    genre: string;
    spotify_preview_url?: string;
    spotify_url?: string;
    discogs_url?: string;
    cover_url?: string;
    reasoning?: string;
}

export interface SearchRequest {
    query: string;
    max_results?: number;
    include_spotify?: boolean;
    include_discogs?: boolean;
}

export interface SearchResponse {
    query: string;
    recommendations: AlbumData[];  // Keep this for search results
    total_found: number;
    processing_time_ms: number;
}

export interface SuggestionResult {
    id: number;
    type: string;
    title: string;
    year?: string;
    thumb?: string;
}

export interface SuggestionResponse {
    results: SuggestionResult[];
    pagination: {
        per_page: number;
        pages: number;
        page: number;
        items: number;
    };
}


export interface FavoritesWithDetailsResponse {
    success: boolean;
    favorites: FavoriteItem[];
    total: number;
    error?: string;
}

export interface FavoriteItem {
    id: string;
    saved_at: string;
    albums?: AlbumData;
    album?: AlbumData;
    reasoning?: string;
}

export interface FavoriteActionResponse {
    success: boolean;
    message: string;
}

    