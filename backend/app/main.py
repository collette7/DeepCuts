import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import time
import httpx
from pydantic import BaseModel
from app.models.albums import AlbumData, SearchRequest, SearchResponse
from app.models.searchSuggestions import SuggestionRequest, SuggestionResult, SuggestionResponse
from app.config import settings
from app.services.claude import claude_service
import asyncio

load_dotenv()

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


async def get_album_cover_from_discogs(title: str, artist: str) -> Optional[str]:
    """Get high-resolution album cover URL from Discogs API."""
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
        print(f"Error fetching cover from Discogs: {e}")
    
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
            print("No recommendations from Claude")
            recommendations = []
        
        # cover images from Discogs
        if recommendations and request.include_discogs:
            enriched_recommendations = []
            for album in recommendations:
                
                cover_url = await get_album_cover_from_discogs(album.title, album.artist)
                
                # Create new album with cover 
                enriched_album = AlbumData(
                    id=album.id,
                    title=album.title,
                    artist=album.artist,
                    year=album.year,
                    genre=album.genre,
                    spotify_preview_url=album.spotify_preview_url,
                    spotify_url=album.spotify_url,
                    discogs_url=album.discogs_url,
                    cover_url=cover_url
                )
                enriched_recommendations.append(enriched_album)
            
            recommendations = enriched_recommendations
        
        # Limit results
        limited_recommendations = recommendations[:request.max_results]
        
    except Exception as e:
        print(f"Recommendations Error: {e}")
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
    
    # Get Discogs API credentials from environment
    discogs_key = os.getenv("DISCOGS_KEY")
    discogs_secret = os.getenv("DISCOGS_SECRET")
    
    if not discogs_key or not discogs_secret:
        # Return empty results if no API keys
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
        print(f"Discogs API Error: {e}")
        # Return empty results on error
        return SuggestionResponse(
            results=[],
            pagination={"per_page": request.per_page, "pages": 0, "page": 1, "items": 0}
        )

