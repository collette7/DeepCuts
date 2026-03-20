import os
from typing import Any

from dotenv import load_dotenv
from supabase import create_client

from ..models.albums import AlbumData

load_dotenv()


class SearchSessionService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not self.url or not self.key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        self.supabase = create_client(self.url, self.key)

    def create_session(
        self,
        query: str,
        albums: list[AlbumData],
        user_email: str | None = None,
        ai_model: str | None = None,
    ) -> str | None:
        try:
            session_data = {
                "query": query,
                "user_email": user_email,
                "ai_model": ai_model,
                "results_count": len(albums),
            }
            result = self.supabase.table("search_sessions").insert(session_data).execute()
            if not result.data:
                return None
            session_id = result.data[0]["id"]

            if albums:
                album_rows = [
                    {
                        "session_id": session_id,
                        "album_title": a.title,
                        "album_artist": a.artist,
                        "album_year": a.year,
                        "album_genre": a.genre,
                        "rank": i + 1,
                    }
                    for i, a in enumerate(albums)
                    if a.title and a.artist
                ]
                if album_rows:
                    self.supabase.table("search_session_albums").insert(album_rows).execute()

            return session_id

        except Exception as e:
            print(f"Error creating search session: {e}")
            return None

    def track_click(
        self,
        session_id: str,
        album_title: str,
        album_artist: str,
        user_email: str | None = None,
    ) -> None:
        try:
            self.supabase.table("search_session_clicks").insert({
                "session_id": session_id,
                "album_title": album_title,
                "album_artist": album_artist,
                "action": "click",
                "user_email": user_email,
            }).execute()
        except Exception as e:
            print(f"Error tracking click: {e}")

    def track_favorite(
        self,
        session_id: str | None,
        album_title: str,
        album_artist: str,
        favorited: bool,
        user_email: str | None = None,
    ) -> None:
        try:
            if session_id:
                self.supabase.table("search_session_clicks").insert({
                    "session_id": session_id,
                    "album_title": album_title,
                    "album_artist": album_artist,
                    "action": "favorite" if favorited else "unfavorite",
                    "user_email": user_email,
                }).execute()
        except Exception as e:
            print(f"Error tracking favorite: {e}")

    def get_sessions(
        self,
        user_email: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        try:
            q = (
                self.supabase.table("search_sessions")
                .select(
                    "id, query, user_email, ai_model, results_count, created_at,"
                    " search_session_albums(id, album_title, album_artist, album_year, album_genre, rank),"
                    " search_session_clicks!inner(id, album_title, album_artist, action, created_at)"
                )
                .order("created_at", desc=True)
                .limit(limit)
            )
            if user_email:
                q = q.eq("user_email", user_email)
            result = q.execute()
            return result.data or []
        except Exception as e:
            print(f"Error fetching sessions: {e}")
            return []

    def get_session_analytics(self, session_id: str) -> dict[str, Any]:
        try:
            session = (
                self.supabase.table("search_sessions")
                .select(
                    "*,"
                    " search_session_albums(id, album_title, album_artist, album_year, album_genre, rank),"
                    " search_session_clicks(id, album_title, album_artist, action, created_at)"
                )
                .eq("id", session_id)
                .single()
                .execute()
            )
            if not session.data:
                return {}

            clicks = [c for c in session.data.get("search_session_clicks", []) if c.get("action") == "click"]
            favorites = [c for c in session.data.get("search_session_clicks", []) if c.get("action") in ("favorite", "unfavorite")]

            return {
                **session.data,
                "total_clicks": len(clicks),
                "total_favorites": len([f for f in favorites if f.get("action") == "favorite"]),
                "click_rate": len(clicks) / max(session.data.get("results_count", 1), 1),
                "favorite_rate": len([f for f in favorites if f.get("action") == "favorite"]) / max(session.data.get("results_count", 1), 1),
            }
        except Exception as e:
            print(f"Error fetching session analytics: {e}")
            return {}


search_session_service = SearchSessionService()
