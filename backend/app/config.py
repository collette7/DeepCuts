import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "DeepCuts"
    PROJECT_VERSION: str = "0.0.1"
    
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY: Optional[str] = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

settings = Settings()