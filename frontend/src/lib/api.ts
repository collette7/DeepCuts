const API_BASE_URL = 'http://127.0.0.1:8000';

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
                return headers;
            }
            
            if (session?.access_token) {
                headers['Authorization'] = `Bearer ${session.access_token}`;
            }
        } catch (error) {
            console.error('Error getting auth headers:', error);
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
            console.log('Searching albums from:', `${API_BASE_URL}/api/v1/search`);
            const response = await fetch(`${API_BASE_URL}/api/v1/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });
            console.log('Response status:', response.status);
            console.log('Response ok:', response.ok);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Search data:', data);
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    async searchDiscogs(query: string) {
        //Search Discogs for autocomplete
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/discogs/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    query,
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
            const response = await fetch(`${API_BASE_URL}/api/v1/favorites`, {
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
            const response = await fetch(`${API_BASE_URL}/api/v1/favorites/${albumId}`, {
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

    async getFavoritesWithDetails(): Promise<FavoritesWithDetailsResponse> {
        try {
            const headers = await this.getAuthHeaders();
            
            const response = await fetch(`${API_BASE_URL}/api/v1/favorites`, {
                method: 'GET',
                headers: headers
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Get favorites with details error:', error);
            throw error;
        }
    }

    async ensureUserExists() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/auth/ensure-user`, {
                method: 'POST',
                headers: await this.getAuthHeaders()
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Ensure user exists error:', error);
            return { success: false, message: error.message };
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
    recommendations: AlbumData[];
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

export interface FavoritedAlbumWithDetails {
    favorite_id: string;
    saved_at: string;
    source_album: string | null;
    album: AlbumData;
}

export interface FavoritesWithDetailsResponse {
    favorited_albums: FavoritedAlbumWithDetails[];
    favorites_by_source: { [key: string]: FavoritedAlbumWithDetails[] };
    total_count: number;
    error?: string;
}

export interface FavoriteActionResponse {
    success: boolean;
    message: string;
}
    