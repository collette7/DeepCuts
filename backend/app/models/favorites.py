from typing import Optional
from pydantic import BaseModel, Field


class AddToFavoritesRequest(BaseModel):
    """Request to save an album to favorites"""
    album_data: dict = Field(..., description="Full album data to save and favorite")
    source_album_data: Optional[dict] = Field(None, description="The source album data that led to this recommendation")


class FavoriteActionResponse(BaseModel):
    """Response when adding or removing favorites"""
    success: bool = Field(..., description="True if the action worked")
    message: str = Field(..., description="What happened")