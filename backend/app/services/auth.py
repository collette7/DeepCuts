import logging
from dataclasses import dataclass

from fastapi import HTTPException

from app.clients.pocketbase import PocketBaseUnavailableError, get_shared_pocketbase_client

logger = logging.getLogger('deepcuts')


@dataclass
class AuthenticatedUser:
    """Minimal user identity resolved from a PocketBase auth token.

    Mirrors the subset of Supabase's ``user_response.user`` object that
    existing call sites rely on (``.id``, ``.email``), so callers migrating
    off Supabase don't need to change how they read the authenticated user.
    """

    id: str
    email: str


async def get_current_user(token: str) -> AuthenticatedUser:
    """Verify a bearer token against PocketBase and return the user's identity.

    Raises ``HTTPException(401)`` for a missing, invalid, or expired user
    token, and ``HTTPException(503)`` if PocketBase itself is unreachable.
    """
    client = get_shared_pocketbase_client()

    try:
        record = await client.verify_user_token(token)
    except PocketBaseUnavailableError as e:
        logger.error(f"PocketBase unavailable during auth: {e}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from e

    if not record or not record.get("email"):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return AuthenticatedUser(id=record["id"], email=record["email"])
