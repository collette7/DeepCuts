import json

import httpx
import pytest

from app.clients.pocketbase import (
    PocketBaseAuthError,
    PocketBaseClient,
    PocketBaseError,
    PocketBaseUnavailableError,
    escape_filter_value,
)


def make_client(handler) -> PocketBaseClient:
    transport = httpx.MockTransport(handler)
    return PocketBaseClient(
        base_url="http://pocketbase.test",
        admin_email="admin@test.invalid",
        admin_password="admin-password",
        transport=transport,
    )


class TestVerifyUserToken:
    async def test_returns_record_for_valid_token(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"  # PocketBase's auth-refresh is POST-only, GET returns 404
            assert request.url.path == "/api/collections/users/auth-refresh"
            assert request.headers["authorization"] == "user-token"
            return httpx.Response(200, json={"record": {"id": "u1", "email": "a@b.com"}})

        client = make_client(handler)
        record = await client.verify_user_token("user-token")
        assert record == {"id": "u1", "email": "a@b.com"}

    async def test_returns_none_for_invalid_token(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"message": "invalid token"})

        client = make_client(handler)
        record = await client.verify_user_token("bad-token")
        assert record is None

    async def test_timeout_raises_unavailable_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timed out", request=request)

        client = make_client(handler)
        with pytest.raises(PocketBaseUnavailableError):
            await client.verify_user_token("user-token")

    async def test_connect_error_raises_unavailable_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        client = make_client(handler)
        with pytest.raises(PocketBaseUnavailableError):
            await client.verify_user_token("user-token")


class TestAdminAuthentication:
    async def test_authenticates_lazily_on_first_admin_call(self):
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            if request.url.path == "/api/collections/_superusers/auth-with-password":
                return httpx.Response(200, json={"token": "admin-token-1"})
            assert request.headers["authorization"] == "admin-token-1"
            return httpx.Response(200, json={"items": []})

        client = make_client(handler)
        result = await client.list_records("albums")
        assert result == []
        assert calls == [
            "/api/collections/_superusers/auth-with-password",
            "/api/collections/albums/records",
        ]

    async def test_reuses_cached_admin_token_across_calls(self):
        auth_calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal auth_calls
            if request.url.path == "/api/collections/_superusers/auth-with-password":
                auth_calls += 1
                return httpx.Response(200, json={"token": "admin-token-1"})
            return httpx.Response(200, json={"items": []})

        client = make_client(handler)
        await client.list_records("albums")
        await client.list_records("albums")
        assert auth_calls == 1

    async def test_reauthenticates_once_on_401_and_retries(self):
        auth_calls = 0
        data_calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal auth_calls, data_calls
            if request.url.path == "/api/collections/_superusers/auth-with-password":
                auth_calls += 1
                return httpx.Response(200, json={"token": f"admin-token-{auth_calls}"})

            data_calls += 1
            if request.headers["authorization"] == "admin-token-1":
                return httpx.Response(401, json={"message": "token expired"})
            return httpx.Response(200, json={"items": [{"id": "a1"}]})

        client = make_client(handler)
        result = await client.list_records("albums")
        assert result == [{"id": "a1"}]
        assert auth_calls == 2
        assert data_calls == 2

    async def test_raises_auth_error_when_reauthentication_fails(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/_superusers/auth-with-password":
                return httpx.Response(200, json={"token": "admin-token"})
            return httpx.Response(401, json={"message": "token expired"})

        client = make_client(handler)
        with pytest.raises(PocketBaseAuthError):
            await client.list_records("albums")

    async def test_admin_auth_failure_raises_auth_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"message": "invalid credentials"})

        client = make_client(handler)
        with pytest.raises(PocketBaseAuthError):
            await client.list_records("albums")


class TestListAllRecords:
    async def test_aggregates_across_pages(self):
        pages = {
            1: {"items": [{"id": "a1"}], "page": 1, "totalPages": 2},
            2: {"items": [{"id": "a2"}], "page": 2, "totalPages": 2},
        }

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/_superusers/auth-with-password":
                return httpx.Response(200, json={"token": "admin-token"})
            page = int(request.url.params.get("page", "1"))
            return httpx.Response(200, json=pages[page])

        client = make_client(handler)
        result = await client.list_all_records("albums")
        assert result == [{"id": "a1"}, {"id": "a2"}]

    async def test_single_page_stops_immediately(self):
        request_count = {"list": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/_superusers/auth-with-password":
                return httpx.Response(200, json={"token": "admin-token"})
            request_count["list"] += 1
            return httpx.Response(200, json={"items": [{"id": "a1"}], "page": 1, "totalPages": 1})

        client = make_client(handler)
        result = await client.list_all_records("albums")
        assert result == [{"id": "a1"}]
        assert request_count["list"] == 1


class TestEscapeFilterValue:
    def test_wraps_plain_value_in_quotes(self):
        assert escape_filter_value("OK Computer") == '"OK Computer"'

    def test_escapes_embedded_double_quote(self):
        assert escape_filter_value('Say "hello"') == '"Say \\"hello\\""'

    def test_escapes_embedded_backslash(self):
        assert escape_filter_value("a\\b") == '"a\\\\b"'

    def test_apostrophe_needs_no_escaping_for_double_quoted_filter(self):
        assert escape_filter_value("Guns N' Roses") == '"Guns N\' Roses"'


class TestRequestPasswordReset:
    async def test_sends_reset_request(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/collections/users/request-password-reset"
            assert json.loads(request.content) == {"email": "a@b.com"}
            return httpx.Response(204)

        client = make_client(handler)
        await client.request_password_reset("users", "a@b.com")

    async def test_raises_on_failure(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json={"message": "invalid email"})

        client = make_client(handler)
        with pytest.raises(PocketBaseError):
            await client.request_password_reset("users", "a@b.com")


class TestCollectionHelpers:
    async def test_get_record_returns_none_on_404(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/_superusers/auth-with-password":
                return httpx.Response(200, json={"token": "admin-token"})
            return httpx.Response(404, json={"message": "not found"})

        client = make_client(handler)
        record = await client.get_record("albums", "missing-id")
        assert record is None

    async def test_create_record_returns_created_record(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/_superusers/auth-with-password":
                return httpx.Response(200, json={"token": "admin-token"})
            assert request.method == "POST"
            return httpx.Response(201, json={"id": "new-id", "title": "OK Computer"})

        client = make_client(handler)
        record = await client.create_record("albums", {"title": "OK Computer"})
        assert record == {"id": "new-id", "title": "OK Computer"}

    async def test_create_record_raises_on_unexpected_status(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/_superusers/auth-with-password":
                return httpx.Response(200, json={"token": "admin-token"})
            return httpx.Response(400, json={"message": "validation failed"})

        client = make_client(handler)
        with pytest.raises(PocketBaseError):
            await client.create_record("albums", {})

    async def test_delete_record_accepts_204(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/_superusers/auth-with-password":
                return httpx.Response(200, json={"token": "admin-token"})
            assert request.method == "DELETE"
            return httpx.Response(204)

        client = make_client(handler)
        await client.delete_record("albums", "a1")
