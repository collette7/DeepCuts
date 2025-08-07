from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class RecommendationSessionRequest(BaseModel):
    query: str
    source_album_id: Optional[str] = None
    enhancer_settings: Dict[str, Any] = {}
    max_results: int = 10
    include_spotify: bool = True
    include_discogs: bool = True


class Recommendation(BaseModel):
    id: str
    session_id: str
    recommended_album_id: str
    similarity_score: Optional[float] = None
    reason: Optional[str] = None
    rank_order: int
    # Include album details for convenience
    album_title: Optional[str] = None
    album_artist: Optional[str] = None
    album_year: Optional[int] = None
    album_genre: Optional[str] = None
    cover_url: Optional[str] = None
    spotify_url: Optional[str] = None


class RecommendationSession(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    source_album_id: Optional[str] = None
    query: str
    enhancer_settings: Dict[str, Any] = {}
    created_at: datetime
    recommendations: List[Recommendation] = []


class RecommendationSessionResponse(BaseModel):
    success: bool
    session: Optional[RecommendationSession] = None
    message: Optional[str] = None


class RecommendationSessionsList(BaseModel):
    success: bool
    sessions: List[RecommendationSession] = []
    total: int = 0
    message: Optional[str] = None


class CreateRecommendationSessionResponse(BaseModel):
    success: bool
    session_id: Optional[str] = None
    recommendations: List[Recommendation] = []
    message: Optional[str] = None