import logging

from app.clients.pocketbase import (
    PocketBaseError,
    escape_filter_value,
    get_shared_pocketbase_client,
)
from app.models.favorites import AddToFavoritesRequest, FavoriteActionResponse, UserFavoritesList

logger = logging.getLogger('deepcuts')

_ALBUM_METADATA_FIELDS = [
    ('year', 'release_year'),
    ('genre', 'genre'),
    ('discogs_id', 'discogs_id'),
    ('cover_url', 'cover_url'),
    ('spotify_preview_url', 'spotify_preview_url'),
    ('spotify_url', 'spotify_url'),
]


class FavoritesService:
    def __init__(self):
        self.client = get_shared_pocketbase_client()

    async def _find_album_by_title_artist(self, title: str, artist: str) -> dict | None:
        """Case-insensitive exact match on (title, artist), mirroring the
        original Supabase .ilike().ilike() lookup. PocketBase's `~` filter
        operator is a substring/LIKE match rather than exact equality, so
        candidates are narrowed via `~` then confirmed with an exact
        case-insensitive comparison in Python.
        """
        candidates = await self.client.list_records(
            "albums",
            filter=f"title ~ {escape_filter_value(title)} && artist ~ {escape_filter_value(artist)}",
        )
        title_l, artist_l = title.strip().lower(), artist.strip().lower()
        for candidate in candidates:
            if candidate['title'].strip().lower() == title_l and candidate['artist'].strip().lower() == artist_l:
                return candidate
        return None

    async def _find_or_create_album(self, title: str, artist: str, album_data: dict) -> str | None:
        existing = await self._find_album_by_title_artist(title, artist)

        if existing:
            update_fields = {
                dst: album_data[src]
                for src, dst in _ALBUM_METADATA_FIELDS
                if album_data.get(src)
            }
            if update_fields:
                try:
                    await self.client.update_record("albums", existing['id'], update_fields)
                except PocketBaseError as e:
                    logger.error(f"Error updating album metadata: {e}")
            return existing['id']

        insert_data = {'title': title, 'artist': artist}
        insert_data.update({
            dst: album_data[src]
            for src, dst in _ALBUM_METADATA_FIELDS
            if album_data.get(src)
        })
        try:
            created = await self.client.create_record("albums", insert_data)
            return created['id']
        except PocketBaseError as e:
            logger.error(f"Error inserting album: {e}")
            return None

    async def add_to_favorites(self, user_id: str, user_email: str, request: AddToFavoritesRequest) -> FavoriteActionResponse:
        """Add an album to the user's favorites.

        ``user_id`` is the caller's PocketBase user record id. ``user_email``
        is accepted for call-site parity with the pre-migration signature but
        isn't needed here — PocketBase's `users` collection is the single
        source of identity now, so there's no separate public.users lookup.
        """
        try:
            album_data = request.album_data
            title = album_data['title'].strip()
            artist = album_data['artist'].strip()

            album_id = await self._find_or_create_album(title, artist, album_data)
            if not album_id:
                return FavoriteActionResponse(success=False, message="Failed to save album")

            existing = await self.client.list_records(
                "favorites",
                filter=f"user = {escape_filter_value(user_id)} && album = {escape_filter_value(album_id)}",
            )
            if existing:
                return FavoriteActionResponse(success=True, message="Album already in favorites")

            favorite_data = {'user': user_id, 'album': album_id}
            if album_data.get('reasoning'):
                favorite_data['reasoning'] = album_data['reasoning']

            await self.client.create_record("favorites", favorite_data)
            return FavoriteActionResponse(success=True, message="Album added to favorites")

        except PocketBaseError as e:
            logger.error(f"Error adding to favorites: {e}")
            return FavoriteActionResponse(success=False, message=f"Failed to add to favorites: {e}")

    async def remove_from_favorites(self, user_id: str, album_id: str) -> FavoriteActionResponse:
        """Remove an album from the user's favorites.

        ``user_id`` is the caller's PocketBase user record id.
        """
        try:
            existing = await self.client.list_records(
                "favorites",
                filter=f"user = {escape_filter_value(user_id)} && album = {escape_filter_value(album_id)}",
            )
            if not existing:
                return FavoriteActionResponse(success=False, message="Album not found in favorites")

            await self.client.delete_record("favorites", existing[0]['id'])
            return FavoriteActionResponse(success=True, message="Album removed from favorites")

        except PocketBaseError as e:
            logger.error(f"Error removing from favorites: {e}")
            return FavoriteActionResponse(success=False, message=f"Failed to remove from favorites: {e}")

    async def get_user_favorites(self, user_id: str, user_token: str | None = None) -> UserFavoritesList:
        """Get all favorited albums for a user, with full album details.

        ``user_token`` is accepted for call-site parity with the
        pre-migration signature (previously used to build an RLS-scoped
        Supabase client); PocketBase rules are enforced server-side via the
        admin client here since FastAPI already authenticated the caller.
        """
        del user_token  # unused; see docstring
        try:
            favorites = await self.client.list_records(
                "favorites",
                filter=f"user = {escape_filter_value(user_id)}",
                sort="-created",
                expand="album",
            )

            results = []
            for fav in favorites:
                album = fav.get('expand', {}).get('album')
                if not album:
                    continue
                results.append({
                    'id': fav['id'],
                    'saved_at': fav['created'],
                    'reasoning': fav.get('reasoning', ''),
                    'albums': album,
                })

            return UserFavoritesList(success=True, favorites=results, total=len(results))

        except PocketBaseError as e:
            logger.error(f"Error getting favorites: {e}")
            return UserFavoritesList(success=False, favorites=[], total=0)

    async def save_album(self, user_id: str, album_data: dict) -> FavoriteActionResponse:
        """Save album method for authenticated endpoints."""
        try:
            return await self.add_to_favorites(user_id, "", AddToFavoritesRequest(album_data=album_data))
        except PocketBaseError as e:
            logger.error(f"Error in save_album: {e}")
            return FavoriteActionResponse(success=False, message=f"Failed to save album: {e}")

    async def remove_album(self, user_id: str, album_id: str) -> FavoriteActionResponse:
        """Remove album method for authenticated endpoints."""
        return await self.remove_from_favorites(user_id, album_id)

    async def update_favorite(self, user_id: str, album_id: str, album_data: dict) -> FavoriteActionResponse:
        """Update album metadata for a favorite entry.

        ``user_id`` is the caller's PocketBase user record id; only used to
        confirm the favorite belongs to them before updating the shared
        album record.
        """
        try:
            existing = await self.client.list_records(
                "favorites",
                filter=f"user = {escape_filter_value(user_id)} && album = {escape_filter_value(album_id)}",
            )
            if not existing:
                return FavoriteActionResponse(success=False, message="Favorite not found")

            update_data = {}
            if 'spotify_url' in album_data:
                update_data['spotify_url'] = album_data['spotify_url']
            if 'spotify_preview_url' in album_data:
                update_data['spotify_preview_url'] = album_data['spotify_preview_url']
            if 'discogs_url' in album_data:
                update_data['discogs_id'] = album_data['discogs_url']
            if 'cover_url' in album_data:
                update_data['cover_url'] = album_data['cover_url']

            if update_data:
                await self.client.update_record("albums", album_id, update_data)

            return FavoriteActionResponse(success=True, message="Favorite updated")
        except PocketBaseError as e:
            logger.error(f"Error updating favorite: {e}")
            return FavoriteActionResponse(success=False, message=f"Failed to update favorite: {e}")

    async def get_favorites_with_album_details(self, user_id: str, user_token: str | None = None):
        """Get favorites with details, for authenticated endpoints."""
        try:
            favorites_result = await self.get_user_favorites(user_id, user_token)

            return {
                "success": favorites_result.success,
                "favorites": favorites_result.favorites if favorites_result.success else [],
                "total": favorites_result.total,
            }
        except PocketBaseError as e:
            logger.error(f"Error in get_favorites_with_album_details: {e}")
            return {"success": False, "favorites": [], "total": 0}


favorites_service = FavoritesService()
