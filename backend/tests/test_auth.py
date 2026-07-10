import pytest
from fastapi import HTTPException

from app.clients.pocketbase import PocketBaseUnavailableError
from app.services.auth import get_current_user


class FakePocketBaseClient:
    def __init__(self, record=None, error=None):
        self._record = record
        self._error = error

    async def verify_user_token(self, token: str):
        if self._error:
            raise self._error
        return self._record


@pytest.fixture(autouse=True)
def reset_shared_client(monkeypatch):
    # Ensure each test controls exactly which client get_current_user resolves,
    # regardless of module import order / prior test pollution of the singleton.
    import app.services.auth as auth_module

    def patch_client(client):
        monkeypatch.setattr(auth_module, "get_shared_pocketbase_client", lambda: client)

    yield patch_client


async def test_returns_authenticated_user_for_valid_token(reset_shared_client):
    reset_shared_client(FakePocketBaseClient(record={"id": "u1", "email": "listener@deepcuts.casa"}))

    user = await get_current_user("valid-token")

    assert user.id == "u1"
    assert user.email == "listener@deepcuts.casa"


async def test_raises_401_for_invalid_token(reset_shared_client):
    reset_shared_client(FakePocketBaseClient(record=None))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user("bad-token")

    assert exc_info.value.status_code == 401


async def test_raises_401_when_record_missing_email(reset_shared_client):
    reset_shared_client(FakePocketBaseClient(record={"id": "u1"}))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user("valid-token")

    assert exc_info.value.status_code == 401


async def test_raises_503_when_pocketbase_unavailable(reset_shared_client):
    reset_shared_client(FakePocketBaseClient(error=PocketBaseUnavailableError("timed out")))

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user("valid-token")

    assert exc_info.value.status_code == 503
