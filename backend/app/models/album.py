from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class AddAlbum(BaseModel):
    """Add album"""
    title: str = Field(..., description="Album title")
    artist: str = Field(..., description="Primary artist name")
    release_year: Optional[int] = Field(None, description="Release year")
    genre: Optional[str] = Field(None, description="Primary genre")

class Album(AddAlbum):
    """Album model"""
    id: str = Field(..., description="Album ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "A Love Supreme",
                "artist": "John Coltrane", 
                "release_year": 1965,
                "genre": "Jazz"
            }
        }


class AlbumRec(Album):
    """Album rec with similarity scoring."""
    similarity_score: float = Field(
        ..., 
        ge=0.0, 
        le=10.0, 
        description="Similarity score from 0-10"
    )
    reasoning: str = Field(..., description="Why was this album recommended")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Kind of Blue",
                "artist": "Miles Davis",
                "release_year": 1959,
                "genre": "Jazz", 
                "similarity_score": 9.2,
                "reasoning": "Modal jazz masterpiece with similar improvisational brilliance"
            }
        }

class Mood(str, Enum):
    """Mood categories"""


class AlbumLinks(BaseModel):
    """External links for an album."""
    pass