import os
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from ..models.favorites import AddToFavoritesRequest, FavoriteActionResponse, UserFavoritesList


class FavoritesService:
    def __init__(self):
        self.url: str = os.environ.get("SUPABASE_URL")
        self.anon_key: str = os.environ.get("SUPABASE_ANON_KEY")
        self.supabase: Client = create_client(self.url, self.anon_key)
    
    def _get_authenticated_client(self, user_token: str) -> Client:
        """Get a Supabase client with user's access token for RLS"""
    
    async def ensure_user_exists(self, user_id: str, user_email: str) -> bool:
        """Ensure user exists in the users table"""
        try:
            # Check if user already exists
            existing_user = self.supabase.table('users').select('id').eq('email', user_email).execute()
            
            if not existing_user.data:
                # Create user if they don't exist
                self.supabase.table('users').insert({
                    'email': user_email
                }).execute()
                
                # Get the created user
                existing_user = self.supabase.table('users').select('id').eq('email', user_email).execute()
                
            return existing_user.data[0]['id'] if existing_user.data else None
        except Exception as e:
            print(f"Error ensuring user exists: {e}")
            return None

    async def add_to_favorites(self, user_id: str, user_email: str, request: AddToFavoritesRequest) -> FavoriteActionResponse:
        """Add an album to user's favorites"""
        try:
            # Ensure user exists and get their UUID
            user_uuid = await self.ensure_user_exists(user_id, user_email)
            if not user_uuid:
                return FavoriteActionResponse(success=False, message="Failed to create/verify user")

            album_data = request.album_data
            
            # First, save the album data to albums table - only required fields
            album_insert_data = {
                'title': album_data['title'],
                'artist': album_data['artist']
            }
            
            # Add optional fields if they exist
            if album_data.get('year'):
                album_insert_data['release_year'] = album_data['year']
            if album_data.get('genre'):
                album_insert_data['genre'] = album_data['genre']
            if album_data.get('discogs_id'):
                album_insert_data['discogs_id'] = album_data['discogs_id']
            if album_data.get('cover_url'):
                album_insert_data['album_art'] = album_data['cover_url']
            if album_data.get('spotify_preview_url'):
                album_insert_data['spotify_preview_url'] = album_data['spotify_preview_url']
            
            # Use upsert to handle duplicates - let Supabase generate the UUID
            album_result = self.supabase.table('albums').upsert(album_insert_data).execute()
            
            # Get the album ID from the result
            if album_result.data:
                album_uuid = album_result.data[0]['id']
            else:
                # If upsert didn't return data, try to find existing album
                existing_album = self.supabase.table('albums').select('id').eq('title', album_data['title']).eq('artist', album_data['artist']).execute()
                if existing_album.data:
                    album_uuid = existing_album.data[0]['id']
                else:
                    return FavoriteActionResponse(success=False, message="Failed to save album")
            
            # Check if already favorited
            existing = self.supabase.table('favorites').select('id').eq('user_id', user_uuid).eq('album_id', album_uuid).execute()
            
            if existing.data:
                return FavoriteActionResponse(success=True, message="Album already in favorites")
            
            # Add to favorites
            favorite_data = {
                'user_id': user_uuid,
                'album_id': album_uuid
            }
            
            self.supabase.table('favorites').insert(favorite_data).execute()
            
            return FavoriteActionResponse(success=True, message="Album added to favorites")
            
        except Exception as e:
            print(f"Error adding to favorites: {e}")
            return FavoriteActionResponse(success=False, message=f"Failed to add to favorites: {str(e)}")

    async def remove_from_favorites(self, user_id: str, album_id: str) -> FavoriteActionResponse:
        """Remove an album from user's favorites"""
        try:
            # Get user UUID by email (using user_id as email for now)
            user_result = self.supabase.table('users').select('id').eq('email', user_id).execute()
            if not user_result.data:
                return FavoriteActionResponse(success=False, message="User not found")
            
            user_uuid = user_result.data[0]['id']
            
            
            # Get all user favorites and remove the matching one
            favorites = self.supabase.table('favorites').select('id, albums!favorites_album_id_fkey(*)').eq('user_id', user_uuid).execute()
            
            favorite_to_delete = None
            for favorite in favorites.data:
                # Match by album ID (this is a simplified approach)
                if str(favorite['albums']['id']) == album_id:
                    favorite_to_delete = favorite['id']
                    break
            
            if favorite_to_delete:
                result = self.supabase.table('favorites').delete().eq('id', favorite_to_delete).execute()
                return FavoriteActionResponse(success=True, message="Album removed from favorites")
            else:
                return FavoriteActionResponse(success=False, message="Album not found in favorites")
                
        except Exception as e:
            print(f"Error removing from favorites: {e}")
            return FavoriteActionResponse(success=False, message=f"Failed to remove from favorites: {str(e)}")

    async def get_user_favorites(self, user_email: str, user_token: str = None) -> UserFavoritesList:
        """Get all favorited albums for a user with full album details"""
        try:
            # Use authenticated client if token provided (for RLS)
            client = self._get_authenticated_client(user_token) if user_token else self.supabase
            
            # Get user UUID by email
            user_result = client.table('users').select('id').eq('email', user_email).execute()
            if not user_result.data:
                return UserFavoritesList(success=True, favorites=[], total=0)
            
            user_uuid = user_result.data[0]['id']
            
            result = client.table('favorites').select(
                'id, saved_at, albums!favorites_album_id_fkey(*)'
            ).eq('user_id', user_uuid).order('saved_at', desc=True).execute()
            
            favorites = result.data or []
            return UserFavoritesList(success=True, favorites=favorites, total=len(favorites))
            
        except Exception as e:
            print(f"Error getting favorites: {e}")
            return UserFavoritesList(success=False, favorites=[], total=0)


    async def save_album(self, user_id: str, album_data: dict) -> FavoriteActionResponse:
        """Save album method for authenticated endpoints - converts user_id to email lookup"""
        try:
            return await self.add_to_favorites(user_id, user_id, AddToFavoritesRequest(album_data=album_data))
        except Exception as e:
            print(f"Error in save_album: {e}")
            return FavoriteActionResponse(success=False, message=f"Failed to save album: {str(e)}")

    async def remove_album(self, user_id: str, album_id: str) -> FavoriteActionResponse:
        """Remove album method for authenticated endpoints"""
        return await self.remove_from_favorites(user_id, album_id)

    async def get_favorites_with_album_details(self, user_email: str, user_token: str = None):
        """Get favorites with details method for authenticated endpoints"""
        favorites_result = await self.get_user_favorites(user_email, user_token)
        return {
            "success": favorites_result.success,
            "favorites": favorites_result.favorites if favorites_result.success else [],
            "total": favorites_result.total
        }

    def is_album_favorited(self, user_id: str, album_id: str) -> bool:
        """Check if album is favorited - placeholder for now"""

        return False


# Create a global instance
favorites_service = FavoritesService()