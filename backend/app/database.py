from supabase import create_client, Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """Get Supabase client with anon key"""
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        logger.error("Missing SUPABASE_URL or SUPABASE_ANON_KEY")
        raise ValueError("Supabase configuration is incomplete. Please set SUPABASE_URL and SUPABASE_ANON_KEY in your .env file")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_supabase_admin_client() -> Client:
    """Get Supabase client with service role key"""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        raise ValueError("Supabase configuration is incomplete. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env file")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

try:
    supabase: Client = get_supabase_client()
    supabase_admin: Client = get_supabase_admin_client()
except ValueError as e:
    logger.error(f"Failed to initialize Supabase clients: {e}")
    raise