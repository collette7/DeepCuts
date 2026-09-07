
from pydantic import BaseModel, Field, field_validator


class AddToFavoritesRequest(BaseModel):
    """Request to save an album to favorites"""
    album_data: dict = Field(..., description="Full album data to save and favorite")
    source_album_data: dict | None = Field(None, description="The source album data that led to this recommendation")
    search_session_id: str | None = Field(
        None,
        max_length=50,
        description="The search input session that led to this favorite",
    )

    @field_validator("album_data")
    @classmethod
    def validate_album_data(cls, album_data: dict) -> dict:
        for field_name in ("title", "artist"):
            value = album_data.get(field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
            if len(value) > 500:
                raise ValueError(f"{field_name} must be 500 characters or fewer")

        reasoning = album_data.get("reasoning")
        if reasoning is not None and (
            not isinstance(reasoning, str) or len(reasoning) > 2000
        ):
            raise ValueError("reasoning must be a string of 2000 characters or fewer")
        return album_data


class FavoriteActionResponse(BaseModel):
    """Response when adding or removing favorites"""
    success: bool = Field(..., description="True if the action worked")
    message: str = Field(..., description="What happened")


class UserFavoritesList(BaseModel):
    """Response for getting user's favorites list"""
    success: bool = Field(..., description="True if the request worked")
    favorites: list = Field(..., description="List of favorited albums")
    total: int = Field(..., description="Total number of favorites")
