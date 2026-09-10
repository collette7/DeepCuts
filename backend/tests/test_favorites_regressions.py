import json

import httpx

from app.models.favorites import AddToFavoritesRequest
from tests.test_favorites import admin_auth_or, make_service


async def test_reuses_album_created_by_concurrent_save():
    album_lookup_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal album_lookup_count
        path = request.url.path
        if path == "/api/collections/albums/records" and request.method == "GET":
            album_lookup_count += 1
            if album_lookup_count == 1:
                return httpx.Response(200, json={"items": []})
            return httpx.Response(200, json={
                "items": [{"id": "album-1", "title": "OK Computer", "artist": "Radiohead"}],
            })
        if path == "/api/collections/albums/records" and request.method == "POST":
            return httpx.Response(400, json={"message": "Failed to create record."})
        if path == "/api/collections/favorites/records" and request.method == "GET":
            return httpx.Response(200, json={"items": []})
        if path == "/api/collections/favorites/records" and request.method == "POST":
            return httpx.Response(201, json={"id": "fav-1"})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    service = make_service(admin_auth_or(handler))
    request = AddToFavoritesRequest(album_data={"title": "OK Computer", "artist": "Radiohead"})

    result = await service.add_to_favorites("user-1", "listener@deepcuts.casa", request)

    assert result.success is True
    assert album_lookup_count == 2


async def test_maps_discogs_url_to_album_record():
    created_album_data = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/collections/albums/records" and request.method == "GET":
            return httpx.Response(200, json={"items": []})
        if path == "/api/collections/albums/records" and request.method == "POST":
            created_album_data.update(json.loads(request.content))
            return httpx.Response(201, json={"id": "album-1"})
        if path == "/api/collections/favorites/records" and request.method == "GET":
            return httpx.Response(200, json={"items": []})
        if path == "/api/collections/favorites/records" and request.method == "POST":
            return httpx.Response(201, json={"id": "fav-1"})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    service = make_service(admin_auth_or(handler))
    request = AddToFavoritesRequest(album_data={
        "title": "OK Computer",
        "artist": "Radiohead",
        "discogs_url": "https://www.discogs.com/release/123",
    })

    result = await service.add_to_favorites("user-1", "listener@deepcuts.casa", request)

    assert result.success is True
    assert created_album_data["discogs_id"] == "https://www.discogs.com/release/123"
