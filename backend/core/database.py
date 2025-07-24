from supabase import create_client, Client
from core.config import settings

def get_supabase_client() -> Client:
    """Get Supabase client with anon key"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def get_supabase_admin_client() -> Client:
    """Get Supabase client with service role key"""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

supabase: Client = get_supabase_client()
supabase_admin: Client = get_supabase_admin_client()