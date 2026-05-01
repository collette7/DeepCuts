
from uuid import UUID

from pydantic import BaseModel, Field


class AddToFavoritesRequest(BaseModel):
    """Request to save an album to favorites"""
    album_data: dict = Field(..., description="Full album data to save and favorite")
    source_album_data: dict | None = Field(None, description="The source album data that led to this recommendation")
    search_session_id: UUID | None = Field(None, description="The search input session that led to this favorite")


class FavoriteActionResponse(BaseModel):
    """Response when adding or removing favorites"""
    success: bool = Field(..., description="True if the action worked")
    message: str = Field(..., description="What happened")


class UserFavoritesList(BaseModel):
    """Response for getting user's favorites list"""
    success: bool = Field(..., description="True if the request worked")
    favorites: list = Field(..., description="List of favorited albums")
    total: int = Field(..., description="Total number of favorites")
