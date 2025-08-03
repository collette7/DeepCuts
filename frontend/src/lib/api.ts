const API_BASE_URL = 'http://127.0.0.1:8000';

class ApiClient {
    // client for FastAPI 
    // source of truth for all comms with backend

    async getWelcome() {
        //Get welcome message
        const response = await
        fetch(`${API_BASE_URL}/`);
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
    