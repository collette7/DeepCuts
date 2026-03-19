import { apiClient, AlbumData } from './api';

export async function enrichAlbumWithSpotifyData(album: AlbumData): Promise<AlbumData> {
    if (!album?.id || !album.title || !album.artist) {
        return album;
    }

    const spotifyData = await apiClient.getAlbumSpotifyData(album.id, album.title, album.artist);

    return {
        ...album,
        spotify_preview_url: spotifyData.spotify_preview_url,
        spotify_url: spotifyData.spotify_url,
        cover_url: spotifyData.cover_url || album.cover_url,
        discogs_url: spotifyData.discogs_url || album.discogs_url,
    };
}

export async function enrichAlbumsInParallel(
    albums: AlbumData[],
    onAlbumEnriched: (original: AlbumData, enriched: AlbumData) => void,
): Promise<void> {
    const promises = albums.map(async (album) => {
        try {
            const enriched = await enrichAlbumWithSpotifyData(album);
            onAlbumEnriched(album, enriched);
        } catch (error) {
            console.error(`Failed to load Spotify data for ${album.title}:`, error);
        }
    });

    await Promise.all(promises);
}
