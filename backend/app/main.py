import os
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import time
import httpx
from pydantic import BaseModel
from app.models.albums import AlbumData, SearchRequest, SearchResponse
from app.models.searchSuggestions import SuggestionRequest, SuggestionResult, SuggestionResponse
from app.models.favorites import AddToFavoritesRequest, FavoriteActionResponse, UserFavoritesList
from app.config import settings
from app.services.claude import claude_service
from app.services.favorites import favorites_service
from app.database import supabase as db_client
import asyncio
import logging

load_dotenv()

# FastAPI's logging
logger = logging.getLogger("uvicorn")

app = FastAPI(title=settings.PROJECT_NAME, version=settings.PROJECT_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://127.0.0.1:3001"],
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

supabase: Client = create_client(supabase_url, supabase_key)


@app.get("/")
async def root():
    """Health check."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.PROJECT_VERSION,
        "status": "healthy",
        "features": {
            "ai_search": "enabled",
            "spotify_integration": "NULL",
            "playlist_sync": "NULL"
        }
    }


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
async def search_albums(request: SearchRequest) -> SearchResponse:
    """Get album recommendations based on user query."""
    start_time = time.time()
    
    try:
        # Get album recommendations from claude
        recommendations = await claude_service.get_album_recommendations(request.query)
        
        # Return empty results if claude returns no recommendations
        if not recommendations or len(recommendations) == 0:
            logger.warning(f"No recommendations from Claude for query: {request.query}")
            recommendations = []
        
        # Add cover images and Spotify data
        if recommendations:
            enriched_recommendations = []
            for album in recommendations:
                # Get cover image from Discogs
                cover_url = None
                if request.include_discogs:
                    cover_url = await get_album_cover_from_discogs(album.title, album.artist)
                
                # Get Spotify data
                spotify_data = {"preview_url": None, "external_url": None}
                if request.include_spotify:
                    spotify_data = await get_spotify_album_data(album.title, album.artist)
                
                # Create new album 
                enriched_album = AlbumData(
                    id=album.id,
                    title=album.title,
                    artist=album.artist,
                    year=album.year,
                    genre=album.genre,
                    spotify_preview_url=spotify_data["preview_url"],
                    spotify_url=spotify_data["external_url"],
                    discogs_url=album.discogs_url,
                    cover_url=cover_url,
                    reasoning=album.reasoning
                )
                enriched_recommendations.append(enriched_album)
            
            recommendations = enriched_recommendations
        
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
        user_response = db_client.auth.get_user(token)
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user_response.user.id
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


@app.post("/api/v1/favorites/add")
async def add_favorite(
    request: AddToFavoritesRequest,
    user_id: str = Depends(get_current_user)
) -> FavoriteActionResponse:
    """Save album to user favorites"""
    return favorites_service.save_album(user_id, request.album_data)


@app.delete("/api/v1/favorites/remove/{album_id}")
async def remove_favorite(
    album_id: str,
    user_id: str = Depends(get_current_user)
) -> FavoriteActionResponse:
    """Remove an album"""
    return favorites_service.remove_album(user_id, album_id)


@app.get("/api/v1/favorites")
async def get_user_favorites(
    user_id: str = Depends(get_current_user)
) -> UserFavoritesList:
    """Get all of a user's favorite albums"""
    return favorites_service.get_user_favorites(user_id)


@app.get("/api/v1/favorites/with-details")
async def get_favorites_with_details(
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get user's favorites"""
    return favorites_service.get_favorites_with_album_details(user_id)


@app.get("/api/v1/favorites/check/{album_id}")
async def check_if_favorited(
    album_id: str,
    user_id: str = Depends(get_current_user)
) -> Dict[str, bool]:
    """Check if an album is in user favorites"""
    is_favorited = favorites_service.is_album_favorited(user_id, album_id)
    return {"is_favorited": is_favorited}

