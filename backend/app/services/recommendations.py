import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from ..models.recommendations import RecommendationSessionResponse, RecommendationSessionsList
from ..models.albums import AlbumData
from ..config import settings
from dotenv import load_dotenv

load_dotenv()


class RecommendationService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not self.url or not self.service_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        self.supabase = create_client(self.url, self.service_key)

    async def create_recommendation_session(
        self, 
        query: str, 
        user_email: Optional[str] = None,
        source_album: Optional[str] = None,
        enhancer_settings: Dict[str, Any] = None
    ) -> str:
        """Create a new recommendation session"""
        try:
            session_data = {
                "query": query,
                "user_email": user_email,
                "source_album": source_album,
                "enhancer_settings": enhancer_settings or {},
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table('recommendation_sessions').insert(session_data).execute()
            
            if result.data:
                return str(result.data[0]['id'])
            else:
                raise Exception("Failed to create session")
                
        except Exception as e:
            print(f"Error creating recommendation session: {e}")
            raise

    async def save_recommendations(self, session_id: str, recommended_albums: List[AlbumData]):
        """Save recommendations to a session"""
        try:
            # Update the session with recommended albums
            recommended_albums_data = [rec.dict() for rec in recommended_albums]
            
            result = self.supabase.table('recommendation_sessions').update({
                "recommended_albums": recommended_albums_data
            }).eq('id', session_id).execute()
            
            return result.data
            
        except Exception as e:
            print(f"Error saving recommendations: {e}")
            raise



# Create a global instance
recommendation_service = RecommendationService()