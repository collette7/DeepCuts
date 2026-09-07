from typing import Any, Literal

from pydantic import BaseModel, Field


class SuggestionRequest(BaseModel):
    """Search suggestions request for autocomplete fron Discogs"""
    query: str = Field(min_length=1, max_length=200)
    type: Literal["release", "master", "artist", "label"] = "release"
    per_page: int = Field(default=25, ge=1, le=25)


class SuggestionResult(BaseModel):
    """Individual search suggestion result"""
    id: int = 0
    type: str = "release"
    title: str
    artist: str | None = None
    search_query: str
    year: str | None = None
    thumb: str | None = None


class SuggestionResponse(BaseModel):
    """Search suggestions response"""
    results: list[SuggestionResult]
    pagination: dict[str, Any]
