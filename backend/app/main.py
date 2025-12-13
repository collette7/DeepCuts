import logging
import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import Client, create_client

from app.config import settings
from app.database import supabase_admin
from app.models.albums import AlbumData, SearchRequest, SearchResponse
from app.models.favorites import AddToFavoritesRequest, FavoriteActionResponse, UserFavoritesList
from app.models.searchSuggestions import SuggestionRequest, SuggestionResponse, SuggestionResult
from app.services.ai import (
    VALID_CLAUDE_MODELS,
    VALID_GEMINI_MODELS,
    ai_service,
    get_model_info,
    set_active_model,
)
from app.services.favorites import favorites_service
from app.services.recommendations import recommendation_service

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

# Initialize AI service with Supabase client for runtime config
ai_service.supabase = supabase_admin


@app.get("/")
async def root():
    """Health check."""
    # Test Supabase connection
    supabase_status = "unknown"
    try:
        # Try a simple query to test the connection
        supabase_admin.table('users').select('id').limit(1).execute()
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


@app.get("/api/v1/health/ai")
async def ai_health_check():
    """
    Health check endpoint for AI configuration.
    Returns the current AI model status and validates it's working.
    """
    config = ai_service.get_config_status()

    # Check for critical errors
    if config.get("validation_error"):
        return {
            "status": "error",
            "message": config["validation_error"],
            **config
        }

    if config.get("is_deprecated"):
        return {
            "status": "error",
            "message": f"Model '{config['active_model']}' is deprecated and will not work",
            **config
        }

    return {
        "status": "healthy" if config["model_validated"] else "warning",
        "message": "AI service configured" if config["model_validated"] else "Model not in known valid list",
        **config
    }


@app.get("/api/v1/health/ai/verify")
async def verify_ai_model():
    """
    Verify the AI model by making a test API call.
    This is more expensive but confirms the model actually works.
    """
    result = await ai_service.verify_model_exists()

    if result["valid"]:
        return {
            "status": "healthy",
            "message": f"Model '{result['model']}' is working correctly",
            **result
        }
    else:
        return {
            "status": "error",
            "message": result.get("error", "Model verification failed"),
            **result
        }


# =============================================
# Settings Management Endpoints
# =============================================

@app.get("/api/v1/settings/models")
async def get_available_models():
    """
    Get all available AI models.
    Returns models organized by provider with metadata.
    """
    current_model = ai_service.ACTIVE_MODEL
    current_info = get_model_info(current_model)

    return {
        "current_model": {
            "id": current_model,
            "name": current_info["name"] if current_info else current_model,
            "provider": "gemini" if "gemini" in current_model.lower() else "claude",
            "is_free": current_info["free"] if current_info else False,
        },
        "available_models": {
            "claude": VALID_CLAUDE_MODELS,
            "gemini": VALID_GEMINI_MODELS,
        },
        "note": "Gemini models are free. Change the model via PUT /api/v1/settings/model"
    }


@app.put("/api/v1/settings/model")
async def update_active_model(model_id: str):
    """
    Update the active AI model.
    Changes take effect immediately (within 60 seconds due to caching).

    Args:
        model_id: The model ID to switch to (e.g., 'gemini-2.5-flash', 'claude-3-haiku-20240307')
    """
    result = await set_active_model(supabase_admin, model_id)

    if result["success"]:
        return {
            "status": "success",
            "message": f"Active model changed to {result['model_name']}",
            **result
        }
    else:
        raise HTTPException(status_code=400, detail=result["error"])


@app.post("/api/v1/settings/model/refresh")
async def refresh_model_config():
    """
    Force refresh the AI model configuration from Supabase.
    Use this after changing the model in the Supabase dashboard.
    """
    ai_service.supabase = supabase_admin
    new_model = ai_service.refresh_model()
    model_info = get_model_info(new_model)

    return {
        "status": "success",
        "message": f"Model refreshed to {new_model}",
        "model_id": new_model,
        "model_name": model_info["name"] if model_info else new_model,
        "is_free": model_info["free"] if model_info else False,
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
        raise HTTPException(status_code=500, detail="Failed to fetch albums") from e


async def get_spotify_album_data(title: str, artist: str) -> dict[str, str | None]:
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


async def get_discogs_url(title: str, artist: str) -> str | None:
    """Generate Discogs marketplace search URL for an album."""
    import urllib.parse
    search_query = f"{artist} {title}"
    return f"https://www.discogs.com/search/?q={urllib.parse.quote(search_query)}&type=all"


async def get_album_cover_from_discogs(title: str, artist: str) -> str | None:
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
                # Clean up results to remove asterisks from titles
                cleaned_results = []
                for result in data.get("results", []):
                    if "title" in result:
                        result["title"] = (result["title"]
                                         .replace("* -", " -")  # "Artist* -" becomes "Artist -"
                                         .replace("*", "")      # Any remaining asterisks
                                         .strip())
                    cleaned_results.append(SuggestionResult(**result))

                return SuggestionResponse(
                    results=cleaned_results,
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
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}") from e


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
        raise HTTPException(status_code=401, detail="Authentication failed") from e


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
) -> dict[str, Any]:
    """Get user's favorites"""
    token = authorization.replace("Bearer ", "") if authorization else None
    return await favorites_service.get_favorites_with_album_details(user_email, token)


@app.get("/debug/ai-test")
async def debug_ai_test():
    """Debug endpoint to test AI service configuration"""
    try:
        import os

        debug_info = {
            "active_model": os.getenv("ACTIVE_MODEL"),
            "has_claude_key": bool(os.getenv("CLAUDE_API_KEY")),
            "has_gemini_key": bool(os.getenv("GEMINI_API_KEY")),
            "claude_key_preview": os.getenv("CLAUDE_API_KEY", "")[:10] + "..." if os.getenv("CLAUDE_API_KEY") else None,
            "gemini_key_preview": os.getenv("GEMINI_API_KEY", "")[:10] + "..." if os.getenv("GEMINI_API_KEY") else None,
        }

        # Test a simple AI call
        try:
            test_recommendations = await ai_service.get_album_recommendations("Miles Davis Kind of Blue")
            debug_info["ai_test_success"] = True
            debug_info["ai_test_result_count"] = len(test_recommendations)
            if test_recommendations:
                debug_info["ai_test_first_result"] = {
                    "title": test_recommendations[0].title,
                    "artist": test_recommendations[0].artist
                }
        except Exception as ai_error:
            debug_info["ai_test_success"] = False
            debug_info["ai_test_error"] = str(ai_error)

        return debug_info

    except Exception as e:
        return {"error": str(e)}









