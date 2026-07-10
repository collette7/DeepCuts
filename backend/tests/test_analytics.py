from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app
from app.services.auth import AuthenticatedUser


@pytest.fixture
def client():
    return TestClient(app)


def as_user(monkeypatch, email: str, user_id: str = "user-1"):
    monkeypatch.setattr(
        main_module, "authenticate_token", AsyncMock(return_value=AuthenticatedUser(id=user_id, email=email))
    )


def as_unauthenticated(monkeypatch):
    async def raise_401(_token: str):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    monkeypatch.setattr(main_module, "authenticate_token", raise_401)


class TestSessionAnalyticsAuth:
    def test_requires_authorization_header(self, client):
        resp = client.get("/api/v1/analytics/sessions/session-1")
        assert resp.status_code == 401

    def test_rejects_invalid_token(self, client, monkeypatch):
        as_unauthenticated(monkeypatch)

        resp = client.get(
            "/api/v1/analytics/sessions/session-1", headers={"Authorization": "Bearer bad-token"}
        )
        assert resp.status_code == 401

    def test_returns_404_when_session_not_found(self, client, monkeypatch):
        as_user(monkeypatch, "owner@deepcuts.casa")
        monkeypatch.setattr(
            main_module.search_session_service, "get_session_analytics", AsyncMock(return_value={})
        )

        resp = client.get(
            "/api/v1/analytics/sessions/missing", headers={"Authorization": "Bearer good-token"}
        )
        assert resp.status_code == 404

    def test_returns_403_for_non_owner(self, client, monkeypatch):
        as_user(monkeypatch, "other@deepcuts.casa")
        monkeypatch.setattr(
            main_module.search_session_service,
            "get_session_analytics",
            AsyncMock(return_value={"id": "session-1", "user_email": "owner@deepcuts.casa"}),
        )

        resp = client.get(
            "/api/v1/analytics/sessions/session-1", headers={"Authorization": "Bearer good-token"}
        )
        assert resp.status_code == 403

    def test_returns_analytics_for_owner(self, client, monkeypatch):
        as_user(monkeypatch, "owner@deepcuts.casa")
        monkeypatch.setattr(
            main_module.search_session_service,
            "get_session_analytics",
            AsyncMock(return_value={"id": "session-1", "user_email": "owner@deepcuts.casa", "total_clicks": 2}),
        )

        resp = client.get(
            "/api/v1/analytics/sessions/session-1", headers={"Authorization": "Bearer good-token"}
        )
        assert resp.status_code == 200
        assert resp.json()["total_clicks"] == 2


class TestSearchResultsAndSummary:
    def test_search_results_requires_auth(self, client):
        resp = client.get("/api/v1/analytics/search-results")
        assert resp.status_code == 401

    def test_search_results_flattens_session_outputs(self, client, monkeypatch):
        as_user(monkeypatch, "owner@deepcuts.casa")
        monkeypatch.setattr(
            main_module,
            "_fetch_sessions_with_outputs",
            AsyncMock(return_value=[
                {
                    "id": "s1",
                    "query": "radiohead",
                    "user_email": "owner@deepcuts.casa",
                    "created": "2026-01-01",
                    "results_count": 2,
                    "raw_results_count": 2,
                    "filtered_count": 0,
                    "outputs": [
                        {"id": "o1", "album_title": "OK Computer", "album_artist": "Radiohead", "rank": 1},
                        {"id": "o2", "album_title": "Kid A", "album_artist": "Radiohead", "rank": 2},
                    ],
                }
            ]),
        )

        resp = client.get(
            "/api/v1/analytics/search-results", headers={"Authorization": "Bearer good-token"}
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) == 2
        assert results[0]["album_title"] == "OK Computer"
        assert results[0]["input_id"] == "s1"

    def test_search_results_includes_session_with_no_outputs(self, client, monkeypatch):
        as_user(monkeypatch, "owner@deepcuts.casa")
        monkeypatch.setattr(
            main_module,
            "_fetch_sessions_with_outputs",
            AsyncMock(return_value=[
                {
                    "id": "s1", "query": "q", "user_email": "owner@deepcuts.casa", "created": "2026-01-01",
                    "results_count": 0, "raw_results_count": 0, "filtered_count": 0, "outputs": [],
                }
            ]),
        )

        resp = client.get(
            "/api/v1/analytics/search-results", headers={"Authorization": "Bearer good-token"}
        )
        results = resp.json()["results"]
        assert len(results) == 1
        assert results[0]["output_id"] is None

    def test_search_summary_aggregates_albums(self, client, monkeypatch):
        as_user(monkeypatch, "owner@deepcuts.casa")
        monkeypatch.setattr(
            main_module,
            "_fetch_sessions_with_outputs",
            AsyncMock(return_value=[
                {
                    "id": "s1", "query": "radiohead", "user_email": "owner@deepcuts.casa",
                    "created": "2026-01-01", "results_count": 2, "filtered_count": 0,
                    "outputs": [
                        {"album_title": "OK Computer", "album_artist": "Radiohead"},
                        {"album_title": "Kid A", "album_artist": "Radiohead"},
                    ],
                }
            ]),
        )

        resp = client.get(
            "/api/v1/analytics/search-summary", headers={"Authorization": "Bearer good-token"}
        )
        assert resp.status_code == 200
        summary = resp.json()["summaries"][0]
        assert summary["output_count"] == 2
        assert summary["albums"] == ["OK Computer by Radiohead", "Kid A by Radiohead"]

    def test_search_summary_null_albums_when_no_outputs(self, client, monkeypatch):
        as_user(monkeypatch, "owner@deepcuts.casa")
        monkeypatch.setattr(
            main_module,
            "_fetch_sessions_with_outputs",
            AsyncMock(return_value=[
                {
                    "id": "s1", "query": "q", "user_email": "owner@deepcuts.casa", "created": "2026-01-01",
                    "results_count": 0, "filtered_count": 0, "outputs": [],
                }
            ]),
        )

        resp = client.get(
            "/api/v1/analytics/search-summary", headers={"Authorization": "Bearer good-token"}
        )
        summary = resp.json()["summaries"][0]
        assert summary["output_count"] == 0
        assert summary["albums"] is None


class TestSearchSessionsList:
    def test_requires_auth(self, client):
        resp = client.get("/api/v1/analytics/sessions")
        assert resp.status_code == 401

    def test_scopes_to_authenticated_users_email(self, client, monkeypatch):
        as_user(monkeypatch, "owner@deepcuts.casa")
        mock_get_sessions = AsyncMock(return_value=[{"id": "s1"}])
        monkeypatch.setattr(main_module.search_session_service, "get_sessions", mock_get_sessions)

        resp = client.get(
            "/api/v1/analytics/sessions", headers={"Authorization": "Bearer good-token"}
        )
        assert resp.status_code == 200
        assert resp.json()["sessions"] == [{"id": "s1"}]
        mock_get_sessions.assert_awaited_once_with(user_email="owner@deepcuts.casa", limit=50)
