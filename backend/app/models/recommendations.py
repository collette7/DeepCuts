from datetime import datetime
from typing import Any

from pydantic import BaseModel

from .albums import AlbumData


class RecommendationSessionRequest(BaseModel):
    query: str
    source_album: str | None = None
    enhancer_settings: dict[str, Any] | None = {}


class RecommendationSessionResponse(BaseModel):
    id: str
    query: str
    created_at: datetime
    user_email: str | None = None
    source_album: str | None = None
    recommended_albums: list[AlbumData] = []
    enhancer_settings: dict[str, Any] | None = {}


class RecommendationSessionsList(BaseModel):
    sessions: list[RecommendationSessionResponse]
    total: int


class CreateRecommendationSessionResponse(BaseModel):
    session_id: str
    success: bool
    message: str
