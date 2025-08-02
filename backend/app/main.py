import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import List, Dict, Any
import time
from app.models.albums import AlbumData, SearchRequest, SearchResponse
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


@app.post("/api/v1/search")
async def search_albums(request: SearchRequest) -> SearchResponse:
    """Search for albums based on user query."""
    start_time = time.time()
    
    try:
        # Get album recommendations from claude
        recommendations = await claude_service.get_album_recommendations(request.query)
        
        # fallback if claude returns empty results
        if not recommendations or len(recommendations) == 0:
            print("No recommendations, using fallback data")
            recommendations = [
                AlbumData(
                    id="1",
                    title="Kind of Blue",
                    artist="Miles Davis",
                    year=1959,
                    genre="Jazz",
                    spotify_preview_url=None,
                    spotify_url=None,
                    discogs_url=None,
                    cover_url=None  
                ),
                AlbumData(
                    id="2",
                    title="Bitches Brew",
                    artist="Miles Davis",
                    year=1970,
                    genre="Jazz Fusion",
                    spotify_preview_url=None,
                    spotify_url=None,
                    discogs_url=None,
                    cover_url=None
                )
            ]
        
        # Limit results
        limited_recommendations = recommendations[:request.max_results]
        
       
        
    except Exception as e:
        print(f"Recommendations Error: {e}")

        limited_recommendations = [
            AlbumData(
                id="1",
                title="Kind of Blue",
                artist="Miles Davis",
                year=1959,
                genre="Jazz",
                spotify_preview_url=None,
                spotify_url=None,
                discogs_url=None,
                cover_url=None  
            ),
            AlbumData(
                id="2",
                title="Bitches Brew",
                artist="Miles Davis",
                year=1970,
                genre="Jazz Fusion",
                spotify_preview_url=None,
                spotify_url=None,
                discogs_url=None,
                cover_url=None
            )
        ]
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return SearchResponse(
        query=request.query,
        recommendations=limited_recommendations,
        total_found=len(limited_recommendations),
        processing_time_ms=processing_time 
    )

