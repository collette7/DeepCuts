import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from export_supabase_users import to_export_record  # noqa: E402
from import_pocketbase_users import find_existing_user, import_user  # noqa: E402

from app.clients.pocketbase import PocketBaseClient  # noqa: E402


def make_client(handler) -> PocketBaseClient:
    return PocketBaseClient(
        base_url="http://pocketbase.test",
        admin_email="admin@test.invalid",
        admin_password="admin-password",
        transport=httpx.MockTransport(handler),
    )


def admin_auth_or(handler):
    def wrapped(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/collections/_superusers/auth-with-password":
            return httpx.Response(200, json={"token": "admin-token"})
        return handler(request)
    return wrapped


SUPABASE_USER_CONFIRMED = {
    "id": "36c80122-dab1-4cfa-b740-54ffa3430ce4",
    "email": "listener@deepcuts.casa",
    "email_confirmed_at": "2025-08-05T03:24:24.418496Z",
    "created_at": "2025-08-04T16:58:01.151135Z",
    "last_sign_in_at": "2026-06-19T13:12:09.494196Z",
    "encrypted_password": "$2a$10$somehashvalue",
    "confirmation_token": "some-token-value",
    "recovery_token": "another-token-value",
}

SUPABASE_USER_UNCONFIRMED = {
    "id": "868bb9ef-9985-49c5-9f3a-322d64b33d0d",
    "email": "unconfirmed@deepcuts.casa",
    "email_confirmed_at": None,
    "created_at": "2025-08-11T22:36:13.0652Z",
    "last_sign_in_at": None,
    "encrypted_password": "$2a$10$anotherhash",
}


class TestExportRecordShape:
    def test_marks_confirmed_account_correctly(self):
        record = to_export_record(SUPABASE_USER_CONFIRMED)
        assert record["confirmed"] is True
        assert record["email"] == "listener@deepcuts.casa"
        assert record["id"] == "36c80122-dab1-4cfa-b740-54ffa3430ce4"

    def test_marks_unconfirmed_account_correctly(self):
        record = to_export_record(SUPABASE_USER_UNCONFIRMED)
        assert record["confirmed"] is False

    def test_never_includes_password_hash_or_tokens(self):
        record = to_export_record(SUPABASE_USER_CONFIRMED)
        serialized = json.dumps(record)
        assert "encrypted_password" not in record
        assert "confirmation_token" not in record
        assert "recovery_token" not in record
        assert "$2a$" not in serialized  # bcrypt hash prefix, extra defense in depth


class TestImportUser:
    async def test_creates_user_with_matching_verified_status(self):
        created_payload = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/users/records" and request.method == "GET":
                return httpx.Response(200, json={"items": []})
            if request.url.path == "/api/collections/users/records" and request.method == "POST":
                created_payload.update(json.loads(request.content))
                return httpx.Response(201, json={"id": "new-user-id", **created_payload})
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        client = make_client(admin_auth_or(handler))
        result = await import_user(client, to_export_record(SUPABASE_USER_CONFIRMED), send_reset_email=False)

        assert result.startswith("CREATED")
        assert created_payload["email"] == "listener@deepcuts.casa"
        assert created_payload["verified"] is True
        assert "encrypted_password" not in created_payload

    async def test_unconfirmed_account_imports_as_unverified(self):
        created_payload = {}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/users/records" and request.method == "GET":
                return httpx.Response(200, json={"items": []})
            if request.url.path == "/api/collections/users/records" and request.method == "POST":
                created_payload.update(json.loads(request.content))
                return httpx.Response(201, json={"id": "new-user-id", **created_payload})
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        client = make_client(admin_auth_or(handler))
        await import_user(client, to_export_record(SUPABASE_USER_UNCONFIRMED), send_reset_email=False)

        assert created_payload["verified"] is False

    async def test_skips_existing_user_without_creating_duplicate(self):
        create_calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/users/records" and request.method == "GET":
                return httpx.Response(200, json={"items": [{"id": "existing-id", "email": "listener@deepcuts.casa"}]})
            if request.url.path == "/api/collections/users/records" and request.method == "POST":
                create_calls["count"] += 1
                return httpx.Response(201, json={"id": "should-not-happen"})
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        client = make_client(admin_auth_or(handler))
        result = await import_user(client, to_export_record(SUPABASE_USER_CONFIRMED), send_reset_email=False)

        assert result.startswith("SKIPPED")
        assert create_calls["count"] == 0

    async def test_running_twice_does_not_duplicate(self):
        state = {"users": []}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/users/records" and request.method == "GET":
                email = request.url.params.get("filter", "")
                matches = [u for u in state["users"] if u["email"] in email]
                return httpx.Response(200, json={"items": matches})
            if request.url.path == "/api/collections/users/records" and request.method == "POST":
                body = json.loads(request.content)
                new_user = {"id": f"user-{len(state['users']) + 1}", "email": body["email"]}
                state["users"].append(new_user)
                return httpx.Response(201, json=new_user)
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        client = make_client(admin_auth_or(handler))
        record = to_export_record(SUPABASE_USER_CONFIRMED)

        first_result = await import_user(client, record, send_reset_email=False)
        second_result = await import_user(client, record, send_reset_email=False)

        assert first_result.startswith("CREATED")
        assert second_result.startswith("SKIPPED")
        assert len(state["users"]) == 1

    async def test_sends_reset_email_when_requested(self):
        reset_requested = {"value": False}

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/users/records" and request.method == "GET":
                return httpx.Response(200, json={"items": []})
            if request.url.path == "/api/collections/users/records" and request.method == "POST":
                return httpx.Response(201, json={"id": "new-user-id"})
            if request.url.path == "/api/collections/users/request-password-reset":
                reset_requested["value"] = True
                return httpx.Response(204)
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        client = make_client(admin_auth_or(handler))
        await import_user(client, to_export_record(SUPABASE_USER_CONFIRMED), send_reset_email=True)

        assert reset_requested["value"] is True

    async def test_does_not_send_reset_email_by_default(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/api/collections/users/records" and request.method == "GET":
                return httpx.Response(200, json={"items": []})
            if request.url.path == "/api/collections/users/records" and request.method == "POST":
                return httpx.Response(201, json={"id": "new-user-id"})
            if request.url.path == "/api/collections/users/request-password-reset":
                raise AssertionError("should not request password reset unless send_reset_email=True")
            raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

        client = make_client(admin_auth_or(handler))
        await import_user(client, to_export_record(SUPABASE_USER_CONFIRMED), send_reset_email=False)


class TestFindExistingUser:
    async def test_returns_none_when_no_match(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"items": []})

        client = make_client(admin_auth_or(handler))
        result = await find_existing_user(client, "nobody@deepcuts.casa")

        assert result is None

    async def test_returns_matching_record(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"items": [{"id": "u1", "email": "listener@deepcuts.casa"}]})

        client = make_client(admin_auth_or(handler))
        result = await find_existing_user(client, "listener@deepcuts.casa")

        assert result is not None
        assert result["id"] == "u1"
