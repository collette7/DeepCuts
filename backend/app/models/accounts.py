from pydantic import BaseModel, ConfigDict


class AccountDeletionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: bool
    deleted_search_sessions: int
