from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class MoodType(str, Enum):
    """Mood types"""
    pass


class Album(BaseModel):
    """Albumd model"""
    id: str = Field(..., description="Unique album identifier (UUID)")
    title: str = Field(..., description="Album title")
    artist: str = Field(..., description="Primary artist name")
    year: Optional[int] = Field(None, description="Release year")
    genre: str = Field(..., description="Primary genre")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Kind of Blue",
                "artist": "Miles Davis", 
                "year": 1959,
                "genre": "Jazz"
            }
        }


class AlbumData(Album):
    """Album metadata"""
    spotify_preview_url: Optional[str] = Field(None, description="Spotify 30-second preview URL")
    spotify_url: Optional[str] = Field(None, description="Spotify album URL")
    discogs_url: Optional[str] = Field(None, description="Discogs marketplace URL")
    cover_url: Optional[str] = Field(None, description="Album artwork URL")


class SearchRequest(BaseModel):
    """Search requests"""
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Album name to search for"
    )
    max_results: int = Field(
        default=10, 
        ge=1, 
        le=20,
        description="Maximum number of recommendations to return"
    )
    include_spotify: bool = Field(
        default=True,
        description="Include Spotify preview URLs"
    )
    include_discogs: bool = Field(
        default=True,
        description="Include Discogs marketplace links"
    )


class SearchResponse(BaseModel):
    """Search recommendations."""
    query: str = Field(..., description="Original search query")
    recommendations: List[AlbumData] = Field(
        default_factory=list,
        description="List of recommended albums"
    )
    total_found: int = Field(..., description="Total number")
    processing_time_ms: int = Field(..., description="Time taken to process request")
    