import os

os.environ.setdefault("SUPABASE_URL", "http://test.invalid")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-service-key")
os.environ.setdefault("ACTIVE_MODEL", "claude-haiku-4-5-20251001")

from unittest.mock import AsyncMock  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import main as main_module  # noqa: E402
from app.main import app  # noqa: E402
from app.models.albums import AlbumData  # noqa: E402
from app.services.ai import RecommendationResult  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main_module.ai_service, "claude_configured", True)

    fake_albums = [
        AlbumData(id=f"a{i}", title=f"Album {i}", artist=f"Artist {i}", year=1990 + i, genre="rock")
        for i in range(7)
    ]
    monkeypatch.setattr(
        main_module.ai_service,
        "get_album_recommendations",
        AsyncMock(return_value=RecommendationResult(albums=fake_albums, raw_response="raw")),
    )
    monkeypatch.setattr(
        main_module,
        "verify_album_exists",
        AsyncMock(return_value=True),
    )
    return TestClient(app)


def test_search_returns_new_count_fields(client):
    resp = client.post("/api/v1/search", json={"query": "city pop"})
    assert resp.status_code == 200
    body = resp.json()
    assert "attempted_count" in body
    assert "verified_count" in body
    assert "filtered" in body
    assert body["verified_count"] == len(body["recommendations"])


def test_search_does_not_retry_when_some_albums_unverified(client, monkeypatch):
    call_count = {"v": 0}

    async def flaky_verify(title, artist):
        call_count["v"] += 1
        return call_count["v"] % 2 == 0

    monkeypatch.setattr(main_module, "verify_album_exists", flaky_verify)

    ai_calls = {"n": 0}
    orig = main_module.ai_service.get_album_recommendations

    async def counting_ai(*args, **kwargs):
        ai_calls["n"] += 1
        return await orig(*args, **kwargs)

    monkeypatch.setattr(main_module.ai_service, "get_album_recommendations", counting_ai)

    resp = client.post("/api/v1/search", json={"query": "shoegaze"})
    assert resp.status_code == 200
    assert ai_calls["n"] == 1, (
        "Plan 005 removed the auto-retry; the AI must be called exactly once per request."
    )


def test_search_with_exclude_drops_excluded_albums(client):
    resp = client.post(
        "/api/v1/search",
        json={"query": "city pop", "exclude": ["Album 0|Artist 0"]},
    )
    assert resp.status_code == 200
    titles = [a["title"] for a in resp.json()["recommendations"]]
    assert "Album 0" not in titles
