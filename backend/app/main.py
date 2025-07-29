import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import List, Dict, Any
from app.models.album import Album, AddAlbum
from app.config import settings

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
def welcome():
    return {"msg":"Blello errybodie"}

@app.get("/albums", response_model=List[Album])
def get_albums():
    """Fetch all albums"""
    try:
        result = supabase.table('albums').select('id, title, artist, release_year, genre').order('created_at').execute()
        return result.data
        
    except Exception as e:
        print(f"Database error: {e}")
        
        raise HTTPException(
            status_code=500, 
            detail="Failed to fetch albums from database"
        )

@app.post("/albums", response_model=Album)  
def add_album(album: AddAlbum):
    """Add new album"""
    try:
        album_data = album.model_dump()
        print(f"Attempting to insert: {album_data}")
        result = supabase.table('albums').insert(album_data).execute()
        print(f"Insert result: {result}")
        
        return result.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Database error: {e}")
        print(f"Error type: {type(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create album: {str(e)}"
        )