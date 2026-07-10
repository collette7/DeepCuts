import logging
from typing import Any

from app.clients.pocketbase import (
    PocketBaseError,
    escape_filter_value,
    get_shared_pocketbase_client,
)
from app.models.albums import AlbumData

logger = logging.getLogger('deepcuts')

# get_sessions emulates Supabase's `search_session_clicks!inner(...)` (only
# return sessions that have at least one click) by over-fetching candidate
# sessions and filtering in Python, since PocketBase's relation expansion is
# always a left join. This multiplier bounds how many extra candidates we're
# willing to check per request; small hobby-scale traffic makes this cheap.
_SESSIONS_OVERFETCH_MULTIPLIER = 5
_SESSIONS_OVERFETCH_CAP = 200


class SearchSessionService:
    def __init__(self):
        self.client = get_shared_pocketbase_client()

    async def create_session(
        self,
        query: str,
        albums: list[AlbumData],
        user_email: str | None = None,
        ai_model: str | None = None,
        raw_results_count: int = 0,
        filtered_count: int = 0,
        ip_address: str | None = None,
        user_agent: str | None = None,
        raw_response: str | None = None,
    ) -> str | None:
        if not albums:
            return None
        try:
            session = await self.client.create_record("search_inputs", {
                "query": query,
                "user_email": user_email,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "ai_model": ai_model,
                "results_count": len(albums),
                "raw_results_count": raw_results_count,
                "filtered_count": filtered_count,
                "raw_response": raw_response,
            })
            session_id = session["id"]

            for i, a in enumerate(albums):
                if not a.title or not a.artist:
                    continue
                await self.client.create_record("search_outputs", {
                    "session": session_id,
                    "album_title": a.title,
                    "album_artist": a.artist,
                    "album_year": a.year,
                    "album_genre": a.genre,
                    "rank": i + 1,
                })

            return session_id

        except PocketBaseError as e:
            logger.error(f"Error creating search session: {e}")
            return None

    async def track_filtered_albums(
        self,
        session_id: str,
        filtered_albums: list[dict[str, str]],
    ) -> None:
        try:
            for a in filtered_albums:
                if not a.get("title") or not a.get("artist"):
                    continue
                await self.client.create_record("filtered_albums", {
                    "session": session_id,
                    "album_title": a.get("title"),
                    "album_artist": a.get("artist"),
                    "filter_reason": a.get("reason", "not_found"),
                })
        except PocketBaseError as e:
            logger.error(f"Error tracking filtered albums: {e}")

    async def track_click(
        self,
        session_id: str | None,
        album_title: str,
        album_artist: str,
        user_email: str | None = None,
    ) -> None:
        try:
            await self.client.create_record("search_clicks", {
                "session": session_id,
                "album_title": album_title,
                "album_artist": album_artist,
                "action": "click",
                "user_email": user_email,
            })
        except PocketBaseError as e:
            logger.error(f"Error tracking click: {e}")

    async def track_favorite(
        self,
        session_id: str | None,
        album_title: str,
        album_artist: str,
        favorited: bool,
        user_email: str | None = None,
    ) -> None:
        try:
            if session_id:
                await self.client.create_record("search_clicks", {
                    "session": session_id,
                    "album_title": album_title,
                    "album_artist": album_artist,
                    "action": "favorite" if favorited else "unfavorite",
                    "user_email": user_email,
                })
        except PocketBaseError as e:
            logger.error(f"Error tracking favorite: {e}")

    async def get_sessions(
        self,
        user_email: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        try:
            overfetch = min(limit * _SESSIONS_OVERFETCH_MULTIPLIER, _SESSIONS_OVERFETCH_CAP)
            params: dict[str, Any] = {"sort": "-created", "perPage": overfetch}
            if user_email:
                params["filter"] = f"user_email = {escape_filter_value(user_email)}"

            candidates = await self.client.list_records("search_inputs", **params)

            results = []
            for session in candidates:
                clicks = await self.client.list_records(
                    "search_clicks", filter=f"session = {escape_filter_value(session['id'])}"
                )
                if not clicks:
                    continue

                outputs = await self.client.list_records(
                    "search_outputs", filter=f"session = {escape_filter_value(session['id'])}"
                )

                results.append({
                    "id": session["id"],
                    "query": session["query"],
                    "user_email": session.get("user_email"),
                    "ai_model": session.get("ai_model"),
                    "results_count": session.get("results_count"),
                    "raw_results_count": session.get("raw_results_count"),
                    "filtered_count": session.get("filtered_count"),
                    "created_at": session["created"],
                    "search_output": outputs,
                    "search_session_clicks": clicks,
                })

                if len(results) >= limit:
                    break

            return results
        except PocketBaseError as e:
            logger.error(f"Error fetching sessions: {e}")
            return []

    async def get_session_analytics(self, session_id: str) -> dict[str, Any]:
        try:
            session = await self.client.get_record("search_inputs", session_id)
            if not session:
                return {}

            outputs = await self.client.list_records(
                "search_outputs", filter=f"session = {escape_filter_value(session_id)}"
            )
            all_clicks = await self.client.list_records(
                "search_clicks", filter=f"session = {escape_filter_value(session_id)}"
            )
            filtered = await self.client.list_records(
                "filtered_albums", filter=f"session = {escape_filter_value(session_id)}"
            )

            clicks = [c for c in all_clicks if c.get("action") == "click"]
            favorites = [c for c in all_clicks if c.get("action") in ("favorite", "unfavorite")]
            raw_count = session.get("raw_results_count", 0)
            results_count = session.get("results_count", 1)

            return {
                "id": session["id"],
                "query": session["query"],
                "user_email": session.get("user_email"),
                "ai_model": session.get("ai_model"),
                "results_count": session.get("results_count"),
                "raw_results_count": raw_count,
                "filtered_count": session.get("filtered_count"),
                "created_at": session["created"],
                "search_output": outputs,
                "search_session_clicks": all_clicks,
                "search_session_filtered_albums": filtered,
                "total_clicks": len(clicks),
                "total_favorites": len([f for f in favorites if f.get("action") == "favorite"]),
                "total_filtered": len(filtered),
                "click_rate": len(clicks) / max(results_count, 1),
                "favorite_rate": len([f for f in favorites if f.get("action") == "favorite"]) / max(results_count, 1),
                "filter_rate": len(filtered) / max(raw_count, 1) if raw_count else 0,
            }
        except PocketBaseError as e:
            logger.error(f"Error fetching session analytics: {e}")
            return {}


search_session_service = SearchSessionService()
