import hmac

from fastapi import Header, HTTPException

from app.config import settings


async def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    expected_key = settings.ADMIN_API_KEY
    if not expected_key:
        raise HTTPException(status_code=503, detail="Administrator access is not configured")
    if not x_admin_key or not hmac.compare_digest(x_admin_key, expected_key):
        raise HTTPException(status_code=401, detail="Administrator authorization required")
