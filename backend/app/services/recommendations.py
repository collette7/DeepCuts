import os
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from ..models.recommendations import (
    RecommendationSession, 
    Recommendation, 
    RecommendationSessionResponse,
    RecommendationSessionsList,
    CreateRecommendationSessionResponse
)
from ..models.albums import AlbumData


class RecommendationService:
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_ANON_KEY")
        self.supabase: Client = create_client(url, key)

    async def create_recommendation_session(
        self, 
        query: str, 
        user_email: Optional[str] = None,
        source_album_id: Optional[str] = None,
        enhancer_settings: Dict[str, Any] = {}
    ) -> str:
        """Create a new recommendation session and return session_id"""
        try:
            # Get user UUID if email provided
            user_uuid = None
            if user_email:
                user_result = self.supabase.table('users').select('id').eq('email', user_email).execute()
                if user_result.data:
                    user_uuid = user_result.data[0]['id']

            # Create session record
            session_data = {
                'user_id': user_uuid,
                'source_album_id': source_album_id,
                'query': query,
                'enhancer_settings': enhancer_settings,
                'created_at': datetime.utcnow().isoformat()
            }

            result = self.supabase.table('recommendation_sessions').insert(session_data).execute()
            
            if result.data:
                return result.data[0]['id']
            else:
                raise Exception("Failed to create session")

        except Exception as e:
            print(f"Error creating recommendation session: {e}")
            raise

    async def save_recommendations(
        self,
        session_id: str,
        recommendations: List[AlbumData]
    ) -> bool:
        """Save recommendations for a session"""
        try:
            # Prepare recommendation records
            recommendation_records = []
            
            for index, album in enumerate(recommendations):
                # First save the album to albums table if not exists
                album_data = {
                    'title': album.title,
                    'artist': album.artist,
                    'release_year': album.year,
                    'genre': album.genre,
                    'discogs_id': album.id if album.id else None,
                    'album_art': album.cover_url,
                    'spotify_preview_url': album.spotify_preview_url
                }

                # Upsert album
                album_result = self.supabase.table('albums').upsert(album_data).execute()
                
                if album_result.data:
                    album_uuid = album_result.data[0]['id']
                else:
                    # Try to find existing album
                    existing = self.supabase.table('albums').select('id').eq('title', album.title).eq('artist', album.artist).execute()
                    if existing.data:
                        album_uuid = existing.data[0]['id']
                    else:
                        print(f"Failed to save album: {album.title} by {album.artist}")
                        continue

                # Create recommendation record
                recommendation_record = {
                    'session_id': session_id,
                    'recommended_album_id': album_uuid,
                    'reason': album.reasoning,
                    'rank_order': index + 1
                }
                recommendation_records.append(recommendation_record)

            # Batch insert recommendations
            if recommendation_records:
                self.supabase.table('recommendations').insert(recommendation_records).execute()
                return True
            
            return False

        except Exception as e:
            print(f"Error saving recommendations: {e}")
            return False

    async def get_user_sessions(self, user_email: str, limit: int = 20) -> RecommendationSessionsList:
        """Get all recommendation sessions for a user"""
        try:
            # Get user UUID
            user_result = self.supabase.table('users').select('id').eq('email', user_email).execute()
            if not user_result.data:
                return RecommendationSessionsList(success=True, sessions=[], total=0)

            user_uuid = user_result.data[0]['id']

            # Get sessions with recommendations
            sessions_result = self.supabase.table('recommendation_sessions').select(
                'id, source_album_id, query, enhancer_settings, created_at, recommendations(id, recommended_album_id, reason, rank_order, albums(*))'
            ).eq('user_id', user_uuid).order('created_at', desc=True).limit(limit).execute()

            sessions = []
            for session_data in sessions_result.data or []:
                # Build recommendations list
                recommendations = []
                for rec_data in session_data.get('recommendations', []):
                    album = rec_data.get('albums')
                    if album:
                        recommendation = Recommendation(
                            id=rec_data['id'],
                            session_id=session_data['id'],
                            recommended_album_id=rec_data['recommended_album_id'],
                            reason=rec_data['reason'],
                            rank_order=rec_data['rank_order'],
                            album_title=album['title'],
                            album_artist=album['artist'],
                            album_year=album.get('release_year'),
                            album_genre=album.get('genre'),
                            cover_url=album.get('album_art'),
                            spotify_url=album.get('spotify_preview_url')
                        )
                        recommendations.append(recommendation)

                # Sort recommendations by rank
                recommendations.sort(key=lambda x: x.rank_order)

                session = RecommendationSession(
                    id=session_data['id'],
                    user_email=user_email,
                    source_album_id=session_data.get('source_album_id'),
                    query=session_data['query'],
                    enhancer_settings=session_data.get('enhancer_settings', {}),
                    created_at=datetime.fromisoformat(session_data['created_at'].replace('Z', '+00:00')),
                    recommendations=recommendations
                )
                sessions.append(session)

            return RecommendationSessionsList(success=True, sessions=sessions, total=len(sessions))

        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return RecommendationSessionsList(success=False, sessions=[], total=0, message=str(e))

    async def get_session_by_id(self, session_id: str, user_email: Optional[str] = None) -> RecommendationSessionResponse:
        """Get a specific recommendation session"""
        try:
            # Build query
            query = self.supabase.table('recommendation_sessions').select(
                'id, user_id, source_album_id, query, enhancer_settings, created_at, recommendations(id, recommended_album_id, reason, rank_order, albums(*))'
            ).eq('id', session_id)

            # Add user filter if provided
            if user_email:
                user_result = self.supabase.table('users').select('id').eq('email', user_email).execute()
                if user_result.data:
                    query = query.eq('user_id', user_result.data[0]['id'])

            result = query.execute()

            if not result.data:
                return RecommendationSessionResponse(success=False, message="Session not found")

            session_data = result.data[0]

            # Build recommendations
            recommendations = []
            for rec_data in session_data.get('recommendations', []):
                album = rec_data.get('albums')
                if album:
                    recommendation = Recommendation(
                        id=rec_data['id'],
                        session_id=session_data['id'],
                        recommended_album_id=rec_data['recommended_album_id'],
                        reason=rec_data['reason'],
                        rank_order=rec_data['rank_order'],
                        album_title=album['title'],
                        album_artist=album['artist'],
                        album_year=album.get('release_year'),
                        album_genre=album.get('genre'),
                        cover_url=album.get('album_art'),
                        spotify_url=album.get('spotify_preview_url')
                    )
                    recommendations.append(recommendation)

            recommendations.sort(key=lambda x: x.rank_order)

            session = RecommendationSession(
                id=session_data['id'],
                user_email=user_email,
                source_album_id=session_data.get('source_album_id'),
                query=session_data['query'],
                enhancer_settings=session_data.get('enhancer_settings', {}),
                created_at=datetime.fromisoformat(session_data['created_at'].replace('Z', '+00:00')),
                recommendations=recommendations
            )

            return RecommendationSessionResponse(success=True, session=session)

        except Exception as e:
            print(f"Error getting session: {e}")
            return RecommendationSessionResponse(success=False, message=str(e))


# Create global instance
recommendation_service = RecommendationService()