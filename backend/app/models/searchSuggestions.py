from typing import List, Optional, Dict, Any
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
    year: Optional[str] = None
    thumb: Optional[str] = None


class SuggestionResponse(BaseModel):
    """Search suggestions response"""
    results: List[SuggestionResult]
    pagination: Dict[str, Any]
