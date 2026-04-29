import logging
import os
from typing import Any

import httpx

logger = logging.getLogger('deepcuts')

RENDER_API_BASE = "https://api.render.com/v1"


def get_render_headers() -> dict[str, str] | None:
    api_key = os.getenv("RENDER_API_KEY")
    if not api_key:
        return None
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def get_render_service_id() -> str | None:
    return os.getenv("RENDER_SERVICE_ID")


async def update_render_env_var(key: str, value: str) -> dict[str, Any]:
    headers = get_render_headers()
    service_id = get_render_service_id()

    if not headers:
        return {"success": False, "error": "RENDER_API_KEY not configured"}
    if not service_id:
        return {"success": False, "error": "RENDER_SERVICE_ID not configured"}

    url = f"{RENDER_API_BASE}/services/{service_id}/env-vars/{key}"
    body = {"value": value}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=headers, json=body)
            if response.status_code in (200, 201):
                return {"success": True}
            else:
                logger.error(f"Render API error {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "error": f"Render API returned {response.status_code}",
                }
    except Exception as e:
        logger.error(f"Error updating Render env var: {e}")
        return {"success": False, "error": str(e)}
