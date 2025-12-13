from typing import Any

from pydantic import BaseModel


class SuggestionRequest(BaseModel):
    """Search suggestions request for autocomplete fron Discogs"""
    query: str
    type: str = "release"
    per_page: int = 10


class SuggestionResult(BaseModel):
    """Individual search suggestion result"""
    id: int
    type: str
    title: str
    year: str | None = None
    thumb: str | None = None


class SuggestionResponse(BaseModel):
    """Search suggestions response"""
    results: list[SuggestionResult]
    pagination: dict[str, Any]
