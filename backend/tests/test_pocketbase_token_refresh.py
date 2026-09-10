import base64
import json
import time

import httpx

from app.clients.pocketbase import PocketBaseClient


def expired_token() -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"exp": int(time.time()) - 1}).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.signature"


async def test_expired_cached_admin_token_reauthenticates_before_list_request():
    auth_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal auth_calls
        if request.url.path == "/api/collections/_superusers/auth-with-password":
            auth_calls += 1
            return httpx.Response(200, json={"token": "fresh-admin-token"})
        if request.headers["authorization"] == "fresh-admin-token":
            return httpx.Response(200, json={"items": [{"id": "favorite-1"}]})
        return httpx.Response(200, json={"items": []})

    client = PocketBaseClient(
        base_url="http://pocketbase.test",
        admin_email="admin@test.invalid",
        admin_password="admin-password",
        transport=httpx.MockTransport(handler),
    )
    client._admin_token = expired_token()

    records = await client.list_records("favorites")

    assert records == [{"id": "favorite-1"}]
    assert auth_calls == 1
