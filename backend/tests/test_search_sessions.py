import json

import httpx

from app.clients.pocketbase import PocketBaseClient
from app.models.albums import AlbumData
from app.services.search_sessions import SearchSessionService


def make_service(handler) -> SearchSessionService:
    service = SearchSessionService()
    service.client = PocketBaseClient(
        base_url="http://pocketbase.test",
        admin_email="admin@test.invalid",
        admin_password="admin-password",
        transport=httpx.MockTransport(handler),
    )
    return service


def admin_auth_or(handler):
    def wrapped(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/collections/_superusers/auth-with-password":
            return httpx.Response(200, json={"token": "admin-token"})
        return handler(request)
    return wrapped


def make_album(title: str, artist: str) -> AlbumData:
    return AlbumData(id=f"{title}-{artist}", title=title, artist=artist, year=1997, genre="Alternative")


class TestCreateSession:
    async def test_creates_session_and_output_rows(self):
        created_outputs = []

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/collections/search_inputs/records" and request.method == "POST":
                return httpx.Response(201, json={"id": "session-1"})
            if path == "/api/collections/search_outputs/records" and request.method == "POST":
                body = json.loads(request.content)
                assert body["session"] == "session-1"
                created_outputs.append(body)
                return httpx.Response(201, json={"id": f"output-{len(created_outputs)}"})
            raise AssertionError(f"unexpected request: {request.method} {path}")

        service = make_service(admin_auth_or(handler))
        albums = [make_album("OK Computer", "Radiohead"), make_album("Kid A", "Radiohead")]

        session_id = await service.create_session(query="radiohead", albums=albums)

        assert session_id == "session-1"
        assert len(created_outputs) == 2
        assert created_outputs[0]["rank"] == 1
        assert created_outputs[1]["rank"] == 2

    async def test_returns_none_for_empty_albums(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError(f"should not make requests: {request.method} {request.url.path}")

        service = make_service(handler)
        session_id = await service.create_session(query="radiohead", albums=[])

        assert session_id is None

    async def test_skips_albums_missing_title_or_artist(self):
        output_calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/collections/search_inputs/records":
                return httpx.Response(201, json={"id": "session-1"})
            if path == "/api/collections/search_outputs/records":
                output_calls["count"] += 1
                return httpx.Response(201, json={"id": "output-1"})
            raise AssertionError(f"unexpected request: {request.method} {path}")

        service = make_service(admin_auth_or(handler))
        albums = [make_album("", "Radiohead"), make_album("OK Computer", "Radiohead")]

        await service.create_session(query="radiohead", albums=albums)

        assert output_calls["count"] == 1

    async def test_returns_none_when_pocketbase_unavailable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        service = make_service(handler)
        session_id = await service.create_session(query="radiohead", albums=[make_album("OK Computer", "Radiohead")])

        assert session_id is None


class TestTrackFavorite:
    async def test_records_favorite_action(self):
        recorded = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/search_clicks/records":
                recorded.update(json.loads(request.content))
                return httpx.Response(201, json={"id": "click-1"})
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        service = make_service(admin_auth_or(handler))
        await service.track_favorite(
            session_id="session-1",
            album_title="OK Computer",
            album_artist="Radiohead",
            favorited=True,
            user_email="listener@deepcuts.casa",
        )

        assert recorded["action"] == "favorite"
        assert recorded["user_email"] == "listener@deepcuts.casa"

    async def test_records_unfavorite_action(self):
        recorded = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/search_clicks/records":
                recorded.update(json.loads(request.content))
                return httpx.Response(201, json={"id": "click-1"})
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        service = make_service(admin_auth_or(handler))
        await service.track_favorite(
            session_id="session-1", album_title="OK Computer", album_artist="Radiohead", favorited=False
        )

        assert recorded["action"] == "unfavorite"

    async def test_does_nothing_without_session_id(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError(f"should not make requests: {request.method} {request.url.path}")

        service = make_service(handler)
        await service.track_favorite(session_id=None, album_title="X", album_artist="Y", favorited=True)


class TestGetSessions:
    async def test_excludes_sessions_with_no_clicks(self):
        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/collections/search_inputs/records":
                return httpx.Response(200, json={
                    "items": [
                        {"id": "s1", "query": "a", "created": "2026-01-02", "results_count": 1},
                        {"id": "s2", "query": "b", "created": "2026-01-01", "results_count": 1},
                    ]
                })
            if path == "/api/collections/search_clicks/records":
                session_filter = request.url.params.get("filter", "")
                if "s1" in session_filter:
                    return httpx.Response(200, json={"items": [{"id": "c1", "action": "click"}]})
                return httpx.Response(200, json={"items": []})
            if path == "/api/collections/search_outputs/records":
                return httpx.Response(200, json={"items": []})
            raise AssertionError(f"unexpected request: {request.method} {path}")

        service = make_service(admin_auth_or(handler))
        sessions = await service.get_sessions(limit=50)

        assert len(sessions) == 1
        assert sessions[0]["id"] == "s1"

    async def test_stops_once_limit_reached(self):
        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/collections/search_inputs/records":
                return httpx.Response(200, json={
                    "items": [{"id": f"s{i}", "query": "q", "created": "2026-01-01"} for i in range(5)]
                })
            if path == "/api/collections/search_clicks/records":
                return httpx.Response(200, json={"items": [{"id": "c1", "action": "click"}]})
            if path == "/api/collections/search_outputs/records":
                return httpx.Response(200, json={"items": []})
            raise AssertionError(f"unexpected request: {request.method} {path}")

        service = make_service(admin_auth_or(handler))
        sessions = await service.get_sessions(limit=2)

        assert len(sessions) == 2

    async def test_returns_empty_list_when_pocketbase_unavailable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        service = make_service(handler)
        sessions = await service.get_sessions(limit=50)

        assert sessions == []


class TestGetSessionAnalytics:
    async def test_computes_rates_from_related_records(self):
        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/collections/search_inputs/records/session-1":
                return httpx.Response(200, json={
                    "id": "session-1", "query": "q", "created": "2026-01-01",
                    "results_count": 4, "raw_results_count": 8, "filtered_count": 4,
                })
            if path == "/api/collections/search_outputs/records":
                return httpx.Response(200, json={"items": [{"id": "o1"}, {"id": "o2"}]})
            if path == "/api/collections/search_clicks/records":
                return httpx.Response(200, json={"items": [
                    {"id": "c1", "action": "click"},
                    {"id": "c2", "action": "favorite"},
                    {"id": "c3", "action": "unfavorite"},
                ]})
            if path == "/api/collections/filtered_albums/records":
                return httpx.Response(200, json={"items": [{"id": "f1"}, {"id": "f2"}]})
            raise AssertionError(f"unexpected request: {request.method} {path}")

        service = make_service(admin_auth_or(handler))
        analytics = await service.get_session_analytics("session-1")

        assert analytics["total_clicks"] == 1
        assert analytics["total_favorites"] == 1
        assert analytics["total_filtered"] == 2
        assert analytics["click_rate"] == 1 / 4
        assert analytics["filter_rate"] == 2 / 8

    async def test_returns_empty_dict_when_session_not_found(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/search_inputs/records/missing":
                return httpx.Response(404, json={"message": "not found"})
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        service = make_service(admin_auth_or(handler))
        analytics = await service.get_session_analytics("missing")

        assert analytics == {}
