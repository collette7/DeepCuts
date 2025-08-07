from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from .albums import AlbumData


class RecommendationSessionRequest(BaseModel):
    query: str
    source_album: Optional[str] = None
    enhancer_settings: Optional[Dict[str, Any]] = {}


class RecommendationSessionResponse(BaseModel):
    id: str
    query: str
    created_at: datetime
    user_email: Optional[str] = None
    source_album: Optional[str] = None
    recommended_albums: List[AlbumData] = []
    enhancer_settings: Optional[Dict[str, Any]] = {}


class RecommendationSessionsList(BaseModel):
    sessions: List[RecommendationSessionResponse]
    total: int


class CreateRecommendationSessionResponse(BaseModel):
    session_id: str
    success: bool
    message: str