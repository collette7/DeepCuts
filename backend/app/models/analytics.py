from pydantic import BaseModel, ConfigDict, Field


class TrackClickRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=500)
    artist: str = Field(min_length=1, max_length=500)
