from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.rate_limit import RateLimitPolicy, SlidingWindowRateLimiter
from app.services.auth import AuthenticatedUser


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/health/ai/verify"),
        ("post", "/api/v1/health/ai/auto-fix"),
        ("put", "/api/v1/settings/model?model_id=gemini-2.5-flash"),
        ("post", "/api/v1/settings/model/refresh"),
    ],
)
def test_admin_routes_reject_requests_without_admin_key(client, monkeypatch, method, path):
    monkeypatch.setattr(main_module.settings, "ADMIN_API_KEY", "test-admin-key")

    response = getattr(client, method)(path)

    assert response.status_code == 401


def test_admin_route_accepts_matching_admin_key(client, monkeypatch):
    monkeypatch.setattr(main_module.settings, "ADMIN_API_KEY", "test-admin-key")
    set_model = AsyncMock(
        return_value={
            "success": True,
            "model_id": "gemini-2.5-flash",
            "model_name": "Gemini 2.5 Flash",
            "is_free": True,
            "persisted": False,
        }
    )
    monkeypatch.setattr(main_module, "set_active_model", set_model)

    response = client.put(
        "/api/v1/settings/model?model_id=gemini-2.5-flash",
        headers={"X-Admin-Key": "test-admin-key"},
    )

    assert response.status_code == 200
    set_model.assert_awaited_once_with("gemini-2.5-flash")


async def test_rate_limiter_rejects_requests_after_policy_limit():
    now = [100.0]
    limiter = SlidingWindowRateLimiter(clock=lambda: now[0])
    policy = RateLimitPolicy(requests=2, window_seconds=60)

    await limiter.check("search:client-1", policy)
    await limiter.check("search:client-1", policy)

    with pytest.raises(HTTPException) as exc_info:
        await limiter.check("search:client-1", policy)

    assert getattr(exc_info.value, "status_code", None) == 429


async def test_rate_limiter_allows_requests_after_window_expires():
    now = [100.0]
    limiter = SlidingWindowRateLimiter(clock=lambda: now[0])
    policy = RateLimitPolicy(requests=1, window_seconds=60)
    await limiter.check("search:client-1", policy)

    now[0] = 161.0
    await limiter.check("search:client-1", policy)


def test_track_click_requires_authentication(client):
    response = client.post(
        "/api/v1/analytics/track-click",
        json={"session_id": "session-1", "title": "A", "artist": "B"},
    )

    assert response.status_code == 401


def test_track_click_rejects_session_owned_by_another_user(client, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "authenticate_token",
        AsyncMock(
            return_value=AuthenticatedUser(id="user-2", email="other@deepcuts.casa")
        ),
    )
    monkeypatch.setattr(
        main_module.search_session_service,
        "session_belongs_to_user",
        AsyncMock(return_value=False),
    )

    response = client.post(
        "/api/v1/analytics/track-click",
        json={"session_id": "session-1", "title": "A", "artist": "B"},
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 403


def test_add_favorite_rejects_session_owned_by_another_user(client, monkeypatch):
    user = AuthenticatedUser(id="user-2", email="other@deepcuts.casa")
    monkeypatch.setattr(main_module, "authenticate_token", AsyncMock(return_value=user))
    monkeypatch.setattr(
        main_module.search_session_service,
        "session_belongs_to_user",
        AsyncMock(return_value=False),
    )
    add_favorite = AsyncMock()
    monkeypatch.setattr(main_module.favorites_service, "add_to_favorites", add_favorite)

    response = client.post(
        "/api/v1/favorites/add",
        headers={"Authorization": "Bearer valid-token"},
        json={
            "album_data": {"id": "album-1", "title": "A", "artist": "B"},
            "search_session_id": "other-session",
        },
    )

    assert response.status_code == 403
    add_favorite.assert_not_awaited()


def test_add_favorite_rejects_oversized_album_title(client):
    response = client.post(
        "/api/v1/favorites/add",
        headers={"Authorization": "Bearer valid-token"},
        json={"album_data": {"title": "A" * 501, "artist": "B"}},
    )

    assert response.status_code == 422
