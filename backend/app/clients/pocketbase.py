import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger('deepcuts')


class PocketBaseError(Exception):
    """Base error for PocketBase client failures."""


class PocketBaseAuthError(PocketBaseError):
    """Raised when a user or admin token fails to authenticate."""


class PocketBaseUnavailableError(PocketBaseError):
    """Raised when PocketBase cannot be reached or times out."""


class PocketBaseClient:
    """Thin async HTTP adapter around PocketBase's REST API.

    Handles superuser (admin) authentication and automatic token refresh so
    callers never have to deal with PocketBase's expiring admin tokens.
    """

    def __init__(
        self,
        base_url: str,
        admin_email: str,
        admin_password: str,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._admin_email = admin_email
        self._admin_password = admin_password
        self._admin_token: str | None = None
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout, transport=transport)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _authenticate_admin(self) -> str:
        try:
            response = await self._client.post(
                "/api/collections/_superusers/auth-with-password",
                json={"identity": self._admin_email, "password": self._admin_password},
            )
        except httpx.TimeoutException as e:
            raise PocketBaseUnavailableError("Timed out authenticating with PocketBase") from e
        except httpx.HTTPError as e:
            raise PocketBaseUnavailableError(f"Failed to reach PocketBase: {e}") from e

        if response.status_code != 200:
            raise PocketBaseAuthError(
                f"PocketBase admin auth failed: {response.status_code} {response.text}"
            )

        token = response.json().get("token")
        if not token:
            raise PocketBaseAuthError("PocketBase admin auth response missing token")

        self._admin_token = token
        return token

    async def _admin_headers(self, force_refresh: bool = False) -> dict[str, str]:
        if force_refresh or not self._admin_token:
            await self._authenticate_admin()
        return {"Authorization": self._admin_token}

    async def _admin_request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = kwargs.pop("headers", None) or {}
        headers.update(await self._admin_headers())

        response = await self._send(method, path, headers=headers, **kwargs)

        if response.status_code == 401:
            # Admin token expired or was revoked — reauthenticate once and retry.
            headers.update(await self._admin_headers(force_refresh=True))
            response = await self._send(method, path, headers=headers, **kwargs)

            if response.status_code == 401:
                raise PocketBaseAuthError("PocketBase admin reauthentication failed")

        return response

    async def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            return await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as e:
            raise PocketBaseUnavailableError(f"Timed out calling PocketBase {method} {path}") from e
        except httpx.HTTPError as e:
            raise PocketBaseUnavailableError(f"Failed to reach PocketBase: {e}") from e

    # --- Auth ---

    async def verify_user_token(self, token: str) -> dict[str, Any] | None:
        """Verify a user's auth token and return their record, or None if invalid/expired.

        PocketBase's auth-refresh endpoint is POST-only; GET returns 404.
        """
        response = await self._send(
            "POST",
            "/api/collections/users/auth-refresh",
            headers={"Authorization": token},
        )
        if response.status_code != 200:
            return None
        return response.json().get("record")

    async def request_password_reset(self, collection: str, email: str) -> None:
        """Trigger PocketBase's password-reset email for an auth collection record."""
        response = await self._send(
            "POST",
            f"/api/collections/{collection}/request-password-reset",
            json={"email": email},
        )
        if response.status_code not in (200, 204):
            raise PocketBaseError(
                f"Failed to request password reset for {email}: {response.status_code} {response.text}"
            )

    # --- Generic collection helpers ---

    async def list_records(self, collection: str, **params: Any) -> list[dict[str, Any]]:
        response = await self._admin_request(
            "GET", f"/api/collections/{collection}/records", params=params
        )
        if response.status_code != 200:
            raise PocketBaseError(
                f"Failed to list {collection}: {response.status_code} {response.text}"
            )
        return response.json().get("items", [])

    async def list_all_records(
        self, collection: str, page_size: int = 200, **params: Any
    ) -> list[dict[str, Any]]:
        """List every record in a collection, paging through results.

        `list_records` returns a single page (PocketBase defaults to 30 per
        page); this loops until all pages are fetched. Use for collections
        expected to be small enough to hold fully in memory.
        """
        params.pop("page", None)
        params["perPage"] = page_size

        all_items: list[dict[str, Any]] = []
        page = 1
        while True:
            response = await self._admin_request(
                "GET", f"/api/collections/{collection}/records", params={**params, "page": page}
            )
            if response.status_code != 200:
                raise PocketBaseError(
                    f"Failed to list {collection}: {response.status_code} {response.text}"
                )
            data = response.json()
            all_items.extend(data.get("items", []))
            if page >= data.get("totalPages", 1):
                break
            page += 1

        return all_items

    async def get_record(self, collection: str, record_id: str, **params: Any) -> dict[str, Any] | None:
        response = await self._admin_request(
            "GET", f"/api/collections/{collection}/records/{record_id}", params=params
        )
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise PocketBaseError(
                f"Failed to get {collection}/{record_id}: {response.status_code} {response.text}"
            )
        return response.json()

    async def create_record(self, collection: str, data: dict[str, Any]) -> dict[str, Any]:
        response = await self._admin_request(
            "POST", f"/api/collections/{collection}/records", json=data
        )
        if response.status_code not in (200, 201):
            raise PocketBaseError(
                f"Failed to create {collection}: {response.status_code} {response.text}"
            )
        return response.json()

    async def update_record(self, collection: str, record_id: str, data: dict[str, Any]) -> dict[str, Any]:
        response = await self._admin_request(
            "PATCH", f"/api/collections/{collection}/records/{record_id}", json=data
        )
        if response.status_code != 200:
            raise PocketBaseError(
                f"Failed to update {collection}/{record_id}: {response.status_code} {response.text}"
            )
        return response.json()

    async def delete_record(self, collection: str, record_id: str) -> None:
        response = await self._admin_request(
            "DELETE", f"/api/collections/{collection}/records/{record_id}"
        )
        if response.status_code not in (200, 204):
            raise PocketBaseError(
                f"Failed to delete {collection}/{record_id}: {response.status_code} {response.text}"
            )


def escape_filter_value(value: str) -> str:
    """Quote and escape a string for safe interpolation into a PocketBase
    filter expression. PocketBase's REST `filter` param has no placeholder
    substitution (that's a client-side SDK convenience the official JS/Dart
    SDKs provide) — callers building filter strings by hand must escape
    quotes themselves or a value like `Guns N' Roses` breaks the filter
    parser (or worse, lets one field's value inject extra conditions).
    """
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def get_pocketbase_client() -> PocketBaseClient:
    if not settings.POCKETBASE_URL or not settings.POCKETBASE_ADMIN_EMAIL or not settings.POCKETBASE_ADMIN_PASSWORD:
        logger.error("Missing POCKETBASE_URL, POCKETBASE_ADMIN_EMAIL, or POCKETBASE_ADMIN_PASSWORD")
        raise ValueError(
            "PocketBase configuration is incomplete. Please set POCKETBASE_URL, "
            "POCKETBASE_ADMIN_EMAIL, and POCKETBASE_ADMIN_PASSWORD in your .env file"
        )
    return PocketBaseClient(
        base_url=settings.POCKETBASE_URL,
        admin_email=settings.POCKETBASE_ADMIN_EMAIL,
        admin_password=settings.POCKETBASE_ADMIN_PASSWORD,
    )


_shared_client: PocketBaseClient | None = None


def get_shared_pocketbase_client() -> PocketBaseClient:
    """Return a process-wide PocketBase client, created lazily on first use.

    Lazy rather than fail-fast at import time (unlike the Supabase client in
    ``app.database``) so the app can keep starting during the migration
    window before PocketBase env vars are configured. Reusing one client
    across requests is what makes admin-token caching actually work — a new
    client per call would reauthenticate every time.
    """
    global _shared_client
    if _shared_client is None:
        _shared_client = get_pocketbase_client()
    return _shared_client
