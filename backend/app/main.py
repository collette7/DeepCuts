import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import time
import httpx
from app.models.albums import AlbumData, SearchRequest, SearchResponse
from app.models.searchSuggestions import SuggestionRequest, SuggestionResult, SuggestionResponse
from app.models.favorites import AddToFavoritesRequest, FavoriteActionResponse, UserFavoritesList
from app.models.recommendations import (
    RecommendationSessionRequest, 
    RecommendationSessionResponse, 
    RecommendationSessionsList,
    CreateRecommendationSessionResponse
)
from app.config import settings
from app.services.ai import ai_service
from app.services.favorites import favorites_service
from app.services.recommendations import recommendation_service
from app.database import supabase_admin
import logging

load_dotenv()

# FastAPI's logging
logger = logging.getLogger("uvicorn")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)
# Configure CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001", 
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "https://www.deepcuts.casa",
    "https://deepcuts.casa",
    "https://deep-cuts-blue.vercel.app",
    "https://*.vercel.app",  # Allow all Vercel preview deployments
]

# Add frontend URL if specified
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

logger.info(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to Supabase 
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Validate env
if not supabase_url or not supabase_key:
    logger.error("Missing required environment variables: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    raise Exception("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")

# Log key info for debugging (first/last few chars only for security)
if supabase_key:
    key_preview = f"{supabase_key[:10]}...{supabase_key[-10:]}" if len(supabase_key) > 20 else "KEY_TOO_SHORT"
    logger.info(f"Using Supabase service role key: {key_preview}")

supabase: Client = create_client(supabase_url, supabase_key)


@app.get("/")
async def root():
    """Health check."""
    # Test Supabase connection
    supabase_status = "unknown"
    try:
        # Try a simple query to test the connection
        test = supabase_admin.table('users').select('id').limit(1).execute()
        supabase_status = "connected"
    except Exception as e:
        supabase_status = f"error: {str(e)[:50]}"
    
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.PROJECT_VERSION,
        "status": "healthy",
        "supabase_status": supabase_status,
        "features": {
            "ai_search": "enabled",
            "spotify_integration": "enabled",
            "playlist_sync": "coming_soon"
        }
    }


@app.get("/api/v1/albums/random")
async def get_random_albums(limit: int = 10):
    """Get random albums from the Sessions database."""
    try:
        # Get all albums then randomly sample them
        result = supabase_admin.table('albums').select('*').execute()
        
        if not result.data:
            return {"albums": [], "total": 0}
        
        # Randomly sample albums
        import random
        random_albums = random.sample(result.data, min(limit, len(result.data)))
        
        # Convert to AlbumData format
        albums = []
        for album in random_albums:
            album_data = {
                "id": str(album.get('id', '')),
                "title": album.get('title', ''),
                "artist": album.get('artist', ''),
                "year": album.get('release_year'),
                "genre": album.get('genre', ''),
                "cover_url": album.get('cover_url'),
                "spotify_preview_url": album.get('spotify_preview_url'),
                "discogs_url": album.get('discogs_id'),
                "reasoning": album.get('reasoning')
            }
            albums.append(album_data)
        
        return {
            "albums": albums,
            "total": len(albums)
        }
        
    except Exception as e:
        logger.error(f"Error fetching random albums: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch albums")


async def get_spotify_album_data(title: str, artist: str) -> Dict[str, Optional[str]]:
    """Get Spotify album data"""
    spotify_client_id = os.getenv("SPOTIFY_CLIENT_ID")
    spotify_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    
    if not spotify_client_id or not spotify_client_secret:
        return {"preview_url": None, "external_url": None}
    
    try:
        async with httpx.AsyncClient() as client:
            # Get Spotify access token
            auth_url = "https://accounts.spotify.com/api/token"
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": spotify_client_id,
                "client_secret": spotify_client_secret
            }
            auth_response = await client.post(auth_url, data=auth_data)
            
            if auth_response.status_code != 200:
                return {"preview_url": None, "external_url": None}
            
            access_token = auth_response.json().get("access_token")
            
            # Search for album
            search_query = f"album:{title} artist:{artist}"
            search_url = "https://api.spotify.com/v1/search"
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {
                "q": search_query,
                "type": "album",
                "limit": 5
            }
            
            search_response = await client.get(search_url, headers=headers, params=params)
            
            if search_response.status_code == 200:
                data = search_response.json()
                albums = data.get("albums", {}).get("items", [])
                
                # Find best match
                for album in albums:
                    album_name = album.get("name", "").lower()
                    album_artists = [artist.get("name", "").lower() for artist in album.get("artists", [])]
                    
                    if (title.lower() in album_name or album_name in title.lower()) and \
                        any(artist.lower() in album_artist for album_artist in album_artists):
                        
                        # Get album tracks for preview URL
                        album_id = album.get("id")
                        if album_id:
                            tracks_url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
                            tracks_response = await client.get(tracks_url, headers=headers)
                            
                            if tracks_response.status_code == 200:
                                tracks_data = tracks_response.json()
                                tracks = tracks_data.get("items", [])
                                
                                # Find a track with preview URL
                                preview_url = None
                                for track in tracks:
                                    if track.get("preview_url"):
                                        preview_url = track.get("preview_url")
                                        break
                                
                                return {
                                    "preview_url": preview_url,
                                    "external_url": album.get("external_urls", {}).get("spotify")
                                }
                        
                        return {
                            "preview_url": None,
                            "external_url": album.get("external_urls", {}).get("spotify")
                        }
                
    except Exception as e:
        logger.error(f"Spotify API error for {title} by {artist}: {e}")
    
    return {"preview_url": None, "external_url": None}


async def get_discogs_url(title: str, artist: str) -> Optional[str]:
    """Generate Discogs marketplace search URL for an album."""
    import urllib.parse
    search_query = f"{artist} {title}"
    return f"https://www.discogs.com/search/?q={urllib.parse.quote(search_query)}&type=all"


async def get_album_cover_from_discogs(title: str, artist: str) -> Optional[str]:
    """Get album cover URL from Discogs API."""
    discogs_key = os.getenv("DISCOGS_KEY")
    discogs_secret = os.getenv("DISCOGS_SECRET")
    
    if not discogs_key or not discogs_secret:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            # Search for the specific album
            search_query = f"{artist} {title}"
            url = "https://api.discogs.com/database/search"
            params = {
                "q": search_query,
                "type": "release",
                "per_page": 5,
                "key": discogs_key,
                "secret": discogs_secret
            }
            headers = {
                "User-Agent": "DeepCuts/1.0 +http://localhost:8000"
            }
            
            response = await client.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                # Find the best match 
                best_match = None
                for result in results:
                    result_title = result.get("title", "").lower()
                    if artist.lower() in result_title and title.lower() in result_title:
                        best_match = result
                        break
                
                # If no exact match, use first result
                if not best_match and results:
                    best_match = results[0]
                
                if best_match:
                    release_id = best_match.get("id")
                    if release_id:
                        release_url = f"https://api.discogs.com/releases/{release_id}"
                        release_response = await client.get(release_url, params={"key": discogs_key, "secret": discogs_secret}, headers=headers)
                        
                        if release_response.status_code == 200:
                            release_data = release_response.json()
                            images = release_data.get("images", [])
                            
                            for image in images:
                                if image.get("type") == "primary":
                                    return image.get("uri")  # Full resolution image
                            
                            if images:
                                return images[0].get("uri")
                    
                    # Fallback to search result images
                    return best_match.get("cover_image") or best_match.get("thumb")
                    
    except Exception as e:
        logger.error(f"Discogs API error for {title} by {artist}: {e}")
    
    return None


@app.post("/api/v1/search")
async def search_albums(
    request: SearchRequest,
    authorization: str = Header(None)
) -> SearchResponse:
    """Get album recommendations based on user query."""
    start_time = time.time()
    
    # Get user email if authenticated
    user_email = None
    if authorization and authorization.startswith("Bearer "):
        try:
            token = authorization.replace("Bearer ", "")
            user_response = supabase_admin.auth.get_user(token)
            if user_response.user:
                user_email = user_response.user.email
        except Exception as e:
            logger.info(f"Search: Could not authenticate user: {e}")
    
    session_id = None
    
    try:
        # Create recommendation session (for both authenticated and anonymous users)
        try:
            session_id = await recommendation_service.create_recommendation_session(
                query=request.query,
                user_email=user_email,
                source_album=getattr(request, 'source_album', None),
                enhancer_settings={}
            )
        except Exception as e:
            logger.error(f"Failed to create recommendation session: {e}")
        
        # Get album recommendations from claude
        recommendations = await ai_service.get_album_recommendations(request.query)
        
        # Return empty results if claude returns no recommendations
        if not recommendations or len(recommendations) == 0:
            logger.warning(f"No recommendations from Claude for query: {request.query}")
            recommendations = []
        
        # Return AI recommendations immediately without waiting for external API calls
        # External data will be loaded progressively on the frontend
        if recommendations:
            # Just convert to proper AlbumData format without external API calls
            quick_recommendations = []
            for album in recommendations:
                quick_album = AlbumData(
                    id=album.id,
                    title=album.title,
                    artist=album.artist,
                    year=album.year,
                    genre=album.genre,
                    spotify_preview_url=None,  # Will be loaded progressively
                    spotify_url=None,  # Will be loaded progressively
                    discogs_url=album.discogs_url,
                    cover_url=None,  # Will be loaded progressively
                    reasoning=album.reasoning
                )
                quick_recommendations.append(quick_album)
            
            recommendations = quick_recommendations
        
        # Save recommended albums to the session
        if session_id and recommendations:
            try:
                await recommendation_service.save_recommendations(session_id, recommendations)
            except Exception as e:
                logger.error(f"Failed to save recommended albums: {e}")
        
        # Limit results
        limited_recommendations = recommendations[:request.max_results]
        
    except Exception as e:
        logger.error(f"Search error for query '{request.query}': {e}")
        limited_recommendations = []
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return SearchResponse(
        query=request.query,
        recommendations=limited_recommendations,
        total_found=len(limited_recommendations),
        processing_time_ms=processing_time 
    )


@app.get("/api/v1/albums/{album_id}/spotify")
async def get_album_spotify_data(album_id: str, title: str, artist: str):
    """Get Spotify and Discogs data for a specific album"""
    try:
        spotify_data = await get_spotify_album_data(title, artist)
        cover_url = await get_album_cover_from_discogs(title, artist)
        discogs_url = await get_discogs_url(title, artist)
        
        return {
            "album_id": album_id,
            "spotify_preview_url": spotify_data.get("preview_url"),
            "spotify_url": spotify_data.get("external_url"), 
            "cover_url": cover_url,
            "discogs_url": discogs_url
        }
    except Exception as e:
        logger.error(f"Error getting Spotify data for {title} by {artist}: {e}")
        return {
            "album_id": album_id,
            "spotify_preview_url": None,
            "spotify_url": None,
            "cover_url": None
        }


@app.post("/api/v1/discogs/search")
async def search_discogs(request: SuggestionRequest) -> SuggestionResponse:
    """Get search suggestions from Discogs for autocomplete dropdown."""
    
    discogs_key = os.getenv("DISCOGS_KEY")
    discogs_secret = os.getenv("DISCOGS_SECRET")
    
    if not discogs_key or not discogs_secret:
        # Return empty results if no API
        return SuggestionResponse(
            results=[],
            pagination={"per_page": request.per_page, "pages": 0, "page": 1, "items": 0}
        )
    
    try:
        async with httpx.AsyncClient() as client:
            url = "https://api.discogs.com/database/search"
            params = {
                "q": request.query,
                "type": request.type,
                "per_page": request.per_page,
                "key": discogs_key,
                "secret": discogs_secret
            }
            headers = {
                "User-Agent": "DeepCuts/1.0 +http://localhost:8000"
            }
            
            response = await client.get(url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return SuggestionResponse(
                    results=[SuggestionResult(**result) for result in data.get("results", [])],
                    pagination=data.get("pagination", {})
                )
            else:
                raise HTTPException(status_code=response.status_code, detail="Discogs API error")
                
    except Exception as e:
        logger.error(f"Discogs search error for '{request.query}': {e}")
        return SuggestionResponse(
            results=[],
            pagination={"per_page": request.per_page, "pages": 0, "page": 1, "items": 0}
        )


def get_current_user(authorization: str = Header(None)) -> str:
    """Get current user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    # Extract token 
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # Verify token with Supabase and get user
        user_response = supabase_admin.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user_response.user.email
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


@app.post("/api/v1/favorites/add")
async def add_favorite(
    request: AddToFavoritesRequest,
    authorization: str = Header(None)
) -> FavoriteActionResponse:
    """Save album to user favorites"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        # Verify token with Supabase and get user
        user_response = supabase_admin.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = user_response.user
        return await favorites_service.add_to_favorites(user.id, user.email, request)
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@app.delete("/api/v1/favorites/remove/{album_id}")
async def remove_favorite(
    album_id: str,
    user_id: str = Depends(get_current_user)
) -> FavoriteActionResponse:
    """Remove an album"""
    return await favorites_service.remove_album(user_id, album_id)


@app.get("/api/v1/favorites")
async def get_user_favorites(
    user_email: str = Depends(get_current_user),
    authorization: str = Header(None)
) -> UserFavoritesList:
    """Get all of a user's favorite albums"""
    token = authorization.replace("Bearer ", "") if authorization else None
    return await favorites_service.get_user_favorites(user_email, token)


@app.get("/api/v1/favorites/with-details")
async def get_favorites_with_details(
    user_email: str = Depends(get_current_user),
    authorization: str = Header(None)
) -> Dict[str, Any]:
    """Get user's favorites"""
    token = authorization.replace("Bearer ", "") if authorization else None
    return await favorites_service.get_favorites_with_album_details(user_email, token)









