const API_BASE_URL = 'http://localhost:8000';

class ApiClient {
    // client for FastAPI 
    // source of truth for all comms with backend

    async getWelcome() {
        //Get welcome message
        const response = await
        fetch(`${API_BASE_URL}/`);
        return response.json();
    }
    async getAlbums() {
        //Get albums
        try {
            console.log('Fetching albums from:', `${API_BASE_URL}/albums`);
            const response = await fetch(`${API_BASE_URL}/albums`);
            console.log('Response status:', response.status);
            console.log('Response ok:', response.ok);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Albums data:', data);
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }  
}

export const apiClient = new ApiClient();

export interface Album {
    id: string;
    title: string;
    artist: string;
    release_year?: number;
    genre?: string;
}
    