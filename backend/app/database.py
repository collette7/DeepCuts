import logging

from supabase import Client, create_client

from app.config import settings

logger = logging.getLogger(__name__)

def get_supabase_client() -> Client:
    """Get Supabase client with publishable key"""
    if not settings.SUPABASE_URL or not settings.SUPABASE_PUBLISHABLE_KEY:
        logger.error("Missing SUPABASE_URL or SUPABASE_PUBLISHABLE_KEY")
        raise ValueError("Supabase configuration is incomplete. Please set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in your .env file")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_PUBLISHABLE_KEY)

def get_supabase_admin_client() -> Client:
    """Get Supabase client with secret key"""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        logger.error("Missing SUPABASE_URL or SUPABASE_SECRET_KEY")
        raise ValueError("Supabase configuration is incomplete. Please set SUPABASE_URL and SUPABASE_SECRET_KEY in your .env file")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)

try:
    supabase: Client = get_supabase_client()
    supabase_admin: Client = get_supabase_admin_client()
except ValueError as e:
    logger.error(f"Failed to initialize Supabase clients: {e}")
    raise
