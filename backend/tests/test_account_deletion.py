from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.services.accounts import AccountService
from app.services.auth import AuthenticatedUser


@pytest.fixture
def client():
    return TestClient(app)


def test_delete_account_uses_authenticated_identity(client, monkeypatch):
    user = AuthenticatedUser(id="user-1", email="owner@deepcuts.casa")
    monkeypatch.setattr(main_module, "authenticate_token", AsyncMock(return_value=user))
    delete_user_data = AsyncMock(
        return_value={"success": True, "deleted_search_sessions": 2}
    )
    monkeypatch.setattr(main_module.account_service, "delete_user_data", delete_user_data)

    response = client.delete(
        "/api/v1/account",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    delete_user_data.assert_awaited_once_with(user)


class FakeAccountClient:
    def __init__(self) -> None:
        self.deleted: list[tuple[str, str]] = []

    async def list_all_records(self, collection: str, **_params):
        assert collection == "search_inputs"
        return [{"id": "session-1"}, {"id": "session-2"}]

    async def delete_record(self, collection: str, record_id: str) -> None:
        self.deleted.append((collection, record_id))


async def test_account_deletion_removes_sessions_before_user():
    service = AccountService()
    service.client = FakeAccountClient()
    user = AuthenticatedUser(id="user-1", email="owner@deepcuts.casa")

    result = await service.delete_user_data(user)

    assert result.deleted_search_sessions == 2
    assert service.client.deleted == [
        ("search_inputs", "session-1"),
        ("search_inputs", "session-2"),
        ("users", "user-1"),
    ]
