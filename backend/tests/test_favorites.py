import httpx

from app.clients.pocketbase import PocketBaseClient
from app.models.favorites import AddToFavoritesRequest
from app.services.favorites import FavoritesService


def make_service(handler) -> FavoritesService:
    service = FavoritesService()
    service.client = PocketBaseClient(
        base_url="http://pocketbase.test",
        admin_email="admin@test.invalid",
        admin_password="admin-password",
        transport=httpx.MockTransport(handler),
    )
    return service


def admin_auth_or(handler):
    """Wrap a handler, auto-answering the admin auth-with-password call so
    each test only needs to model the actual collection request(s)."""
    def wrapped(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/collections/_superusers/auth-with-password":
            return httpx.Response(200, json={"token": "admin-token"})
        return handler(request)
    return wrapped


class TestAddToFavorites:
    async def test_creates_new_album_and_favorite(self):
        created_album = {"id": "album-1", "title": "OK Computer", "artist": "Radiohead"}

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/collections/albums/records" and request.method == "GET":
                return httpx.Response(200, json={"items": []})  # no existing match
            if path == "/api/collections/albums/records" and request.method == "POST":
                return httpx.Response(201, json=created_album)
            if path == "/api/collections/favorites/records" and request.method == "GET":
                return httpx.Response(200, json={"items": []})  # not already favorited
            if path == "/api/collections/favorites/records" and request.method == "POST":
                body = httpx.Request("POST", request.url, content=request.content).content
                assert b'"album-1"' in body
                return httpx.Response(201, json={"id": "fav-1", "user": "user-1", "album": "album-1"})
            raise AssertionError(f"unexpected request: {request.method} {path}")

        service = make_service(admin_auth_or(handler))
        request = AddToFavoritesRequest(album_data={"title": "OK Computer", "artist": "Radiohead"})

        result = await service.add_to_favorites("user-1", "listener@deepcuts.casa", request)

        assert result.success is True
        assert result.message == "Album added to favorites"

    async def test_reuses_existing_album_and_updates_metadata(self):
        existing_album = {"id": "album-1", "title": "OK Computer", "artist": "Radiohead"}
        update_called = {"value": False}

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/collections/albums/records" and request.method == "GET":
                return httpx.Response(200, json={"items": [existing_album]})
            if path == "/api/collections/albums/records/album-1" and request.method == "PATCH":
                update_called["value"] = True
                return httpx.Response(200, json=existing_album)
            if path == "/api/collections/favorites/records" and request.method == "GET":
                return httpx.Response(200, json={"items": []})
            if path == "/api/collections/favorites/records" and request.method == "POST":
                return httpx.Response(201, json={"id": "fav-1"})
            raise AssertionError(f"unexpected request: {request.method} {path}")

        service = make_service(admin_auth_or(handler))
        request = AddToFavoritesRequest(
            album_data={"title": "OK Computer", "artist": "Radiohead", "genre": "Alternative Rock"}
        )

        result = await service.add_to_favorites("user-1", "listener@deepcuts.casa", request)

        assert result.success is True
        assert update_called["value"] is True

    async def test_is_idempotent_for_same_user_and_album(self):
        existing_album = {"id": "album-1", "title": "OK Computer", "artist": "Radiohead"}
        create_favorite_calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/collections/albums/records" and request.method == "GET":
                return httpx.Response(200, json={"items": [existing_album]})
            if path == "/api/collections/favorites/records" and request.method == "GET":
                return httpx.Response(200, json={"items": [{"id": "fav-1", "user": "user-1", "album": "album-1"}]})
            if path == "/api/collections/favorites/records" and request.method == "POST":
                create_favorite_calls["count"] += 1
                return httpx.Response(201, json={"id": "fav-1"})
            raise AssertionError(f"unexpected request: {request.method} {path}")

        service = make_service(admin_auth_or(handler))
        request = AddToFavoritesRequest(album_data={"title": "OK Computer", "artist": "Radiohead"})

        result = await service.add_to_favorites("user-1", "listener@deepcuts.casa", request)

        assert result.success is True
        assert result.message == "Album already in favorites"
        assert create_favorite_calls["count"] == 0

    async def test_returns_failure_when_album_creation_fails(self):
        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/collections/albums/records" and request.method == "GET":
                return httpx.Response(200, json={"items": []})
            if path == "/api/collections/albums/records" and request.method == "POST":
                return httpx.Response(400, json={"message": "validation failed"})
            raise AssertionError(f"unexpected request: {request.method} {path}")

        service = make_service(admin_auth_or(handler))
        request = AddToFavoritesRequest(album_data={"title": "OK Computer", "artist": "Radiohead"})

        result = await service.add_to_favorites("user-1", "listener@deepcuts.casa", request)

        assert result.success is False
        assert "Failed to save album" in result.message


class TestRemoveFromFavorites:
    async def test_removes_existing_favorite(self):
        deleted = {"value": False}

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/collections/favorites/records" and request.method == "GET":
                return httpx.Response(200, json={"items": [{"id": "fav-1"}]})
            if path == "/api/collections/favorites/records/fav-1" and request.method == "DELETE":
                deleted["value"] = True
                return httpx.Response(204)
            raise AssertionError(f"unexpected request: {request.method} {path}")

        service = make_service(admin_auth_or(handler))
        result = await service.remove_from_favorites("user-1", "album-1")

        assert result.success is True
        assert deleted["value"] is True

    async def test_returns_failure_when_not_found(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/favorites/records":
                return httpx.Response(200, json={"items": []})
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        service = make_service(admin_auth_or(handler))
        result = await service.remove_from_favorites("user-1", "album-1")

        assert result.success is False
        assert result.message == "Album not found in favorites"


class TestGetUserFavorites:
    async def test_returns_expanded_album_details(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/favorites/records":
                assert request.url.params.get("expand") == "album"
                return httpx.Response(200, json={
                    "items": [{
                        "id": "fav-1",
                        "created": "2026-01-01 00:00:00.000Z",
                        "reasoning": "great album",
                        "expand": {"album": {"id": "album-1", "title": "OK Computer", "artist": "Radiohead"}},
                    }]
                })
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        service = make_service(admin_auth_or(handler))
        result = await service.get_user_favorites("user-1")

        assert result.success is True
        assert result.total == 1
        assert result.favorites[0]["albums"]["title"] == "OK Computer"

    async def test_skips_favorites_missing_expanded_album(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/favorites/records":
                return httpx.Response(200, json={
                    "items": [{"id": "fav-1", "created": "2026-01-01 00:00:00.000Z", "expand": {}}]
                })
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        service = make_service(admin_auth_or(handler))
        result = await service.get_user_favorites("user-1")

        assert result.success is True
        assert result.total == 0

    async def test_returns_all_favorites_beyond_a_single_page(self):
        # Regression test: get_user_favorites must page through every
        # result, not just PocketBase's default 30-per-page. A user with
        # more favorites than one page previously never saw the rest.
        pages = {
            1: {
                "items": [
                    {"id": f"fav-{i}", "created": "2026-01-01", "expand": {"album": {"id": f"a{i}", "title": f"T{i}", "artist": "X"}}}
                    for i in range(30)
                ],
                "page": 1,
                "totalPages": 2,
            },
            2: {
                "items": [
                    {"id": "fav-30", "created": "2026-01-01", "expand": {"album": {"id": "a30", "title": "T30", "artist": "X"}}}
                ],
                "page": 2,
                "totalPages": 2,
            },
        }

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/favorites/records":
                page = int(request.url.params.get("page", "1"))
                return httpx.Response(200, json=pages[page])
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        service = make_service(admin_auth_or(handler))
        result = await service.get_user_favorites("user-1")

        assert result.total == 31


class TestUpdateFavorite:
    async def test_updates_album_fields_for_owned_favorite(self):
        updated_fields = {}

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if path == "/api/collections/favorites/records" and request.method == "GET":
                return httpx.Response(200, json={"items": [{"id": "fav-1"}]})
            if path == "/api/collections/albums/records/album-1" and request.method == "PATCH":
                import json
                updated_fields.update(json.loads(request.content))
                return httpx.Response(200, json={"id": "album-1"})
            raise AssertionError(f"unexpected request: {request.method} {path}")

        service = make_service(admin_auth_or(handler))
        result = await service.update_favorite("user-1", "album-1", {"spotify_url": "https://open.spotify.com/x"})

        assert result.success is True
        assert updated_fields == {"spotify_url": "https://open.spotify.com/x"}

    async def test_returns_failure_when_favorite_not_owned(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/favorites/records":
                return httpx.Response(200, json={"items": []})
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        service = make_service(admin_auth_or(handler))
        result = await service.update_favorite("user-1", "album-1", {"spotify_url": "x"})

        assert result.success is False
        assert result.message == "Favorite not found"
