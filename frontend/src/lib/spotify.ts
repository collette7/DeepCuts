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

async function enrichBatch(
    albums: AlbumData[],
    onAlbumEnriched: (original: AlbumData, enriched: AlbumData) => void,
): Promise<void> {
    await Promise.all(
        albums.map(async (album) => {
            try {
                const enriched = await enrichAlbumWithSpotifyData(album);
                onAlbumEnriched(album, enriched);
            } catch (error) {
                console.error(`Failed to load Spotify data for ${album.title}:`, error);
            }
        })
    );
}

export async function enrichAlbumsInParallel(
    albums: AlbumData[],
    onAlbumEnriched: (original: AlbumData, enriched: AlbumData) => void,
): Promise<void> {
    const CONCURRENCY = 3;
    for (let i = 0; i < albums.length; i += CONCURRENCY) {
        const batch = albums.slice(i, i + CONCURRENCY);
        await enrichBatch(batch, onAlbumEnriched);
    }
}
