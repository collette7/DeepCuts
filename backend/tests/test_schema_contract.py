import os

import pytest

from app.clients.pocketbase import PocketBaseClient

pytestmark = pytest.mark.asyncio


@pytest.fixture
def pb_client():
    url = os.getenv("POCKETBASE_URL")
    admin_email = os.getenv("POCKETBASE_ADMIN_EMAIL")
    admin_password = os.getenv("POCKETBASE_ADMIN_PASSWORD")
    if not url or not admin_email or not admin_password:
        pytest.skip("POCKETBASE_URL/POCKETBASE_ADMIN_EMAIL/POCKETBASE_ADMIN_PASSWORD not set")
    return PocketBaseClient(base_url=url, admin_email=admin_email, admin_password=admin_password)


@pytest.fixture
async def test_user(pb_client):
    user = await pb_client.create_record(
        "users",
        {
            "email": "schema-contract-test@deepcuts.casa",
            "password": "TestPass123!",
            "passwordConfirm": "TestPass123!",
        },
    )
    yield user
    try:
        await pb_client.delete_record("users", user["id"])
    except Exception:
        pass


@pytest.fixture
async def test_album(pb_client):
    album = await pb_client.create_record(
        "albums", {"title": "Schema Contract Test Album", "artist": "Schema Contract Test Artist"}
    )
    yield album
    try:
        await pb_client.delete_record("albums", album["id"])
    except Exception:
        pass


class TestCollectionsExist:
    async def test_expected_collections_are_present(self, pb_client):
        response = await pb_client._admin_request("GET", "/api/collections", params={"perPage": 50})
        names = {c["name"] for c in response.json()["items"]}

        for expected in [
            "users",
            "albums",
            "favorites",
            "search_inputs",
            "search_outputs",
            "search_clicks",
            "filtered_albums",
        ]:
            assert expected in names

    async def test_users_collection_has_profile_fields(self, pb_client):
        response = await pb_client._admin_request("GET", "/api/collections/users")
        field_names = {f["name"] for f in response.json()["fields"]}

        for expected in ["username", "preferences", "spotify_user_id", "spotify_access_token"]:
            assert expected in field_names


class TestUniqueConstraints:
    async def test_duplicate_album_title_artist_rejected(self, pb_client, test_album):
        with pytest.raises(Exception):  # noqa: B017 — PocketBaseError from create_record's non-2xx check
            await pb_client.create_record(
                "albums", {"title": test_album["title"], "artist": test_album["artist"]}
            )

    async def test_duplicate_favorite_rejected(self, pb_client, test_user, test_album):
        await pb_client.create_record("favorites", {"user": test_user["id"], "album": test_album["id"]})

        with pytest.raises(Exception):  # noqa: B017
            await pb_client.create_record(
                "favorites", {"user": test_user["id"], "album": test_album["id"]}
            )


class TestCascadeDelete:
    async def test_deleting_search_input_cascades_children(self, pb_client):
        session = await pb_client.create_record("search_inputs", {"query": "schema contract test"})
        output = await pb_client.create_record(
            "search_outputs",
            {"session": session["id"], "album_title": "X", "album_artist": "Y"},
        )

        await pb_client.delete_record("search_inputs", session["id"])

        remaining = await pb_client.list_records("search_outputs", filter=f"session='{session['id']}'")
        assert remaining == []
        assert output["session"] == session["id"]  # sanity: child really was linked before delete


class TestAccessRules:
    async def test_unauthenticated_favorites_list_is_empty(self, pb_client):
        # favorites' listRule ("user = @request.auth.id") evaluates auth.id as
        # empty for anonymous requests, so PocketBase returns a filtered empty
        # list (200) rather than an error — verifying no records leak through.
        response = await pb_client._send("GET", "/api/collections/favorites/records")
        assert response.status_code == 200
        assert response.json()["items"] == []

    async def test_cross_user_favorite_not_visible(self, pb_client, test_user, test_album):
        await pb_client.create_record("favorites", {"user": test_user["id"], "album": test_album["id"]})

        owner_token = (
            await pb_client._send(
                "POST",
                "/api/collections/users/auth-with-password",
                json={"identity": test_user["email"], "password": "TestPass123!"},
            )
        ).json()["token"]
        owner_view = await pb_client._send(
            "GET", "/api/collections/favorites/records", headers={"Authorization": owner_token}
        )
        assert len(owner_view.json()["items"]) == 1  # owner can see their own favorite

        other_user = await pb_client.create_record(
            "users",
            {
                "email": "schema-contract-other@deepcuts.casa",
                "password": "OtherPass123!",
                "passwordConfirm": "OtherPass123!",
            },
        )
        try:
            other_token = (
                await pb_client._send(
                    "POST",
                    "/api/collections/users/auth-with-password",
                    json={"identity": other_user["email"], "password": "OtherPass123!"},
                )
            ).json()["token"]

            other_view = await pb_client._send(
                "GET", "/api/collections/favorites/records", headers={"Authorization": other_token}
            )
            assert other_view.json()["items"] == []
        finally:
            await pb_client.delete_record("users", other_user["id"])
