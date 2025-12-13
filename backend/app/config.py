import os

from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "DeepCuts"
    PROJECT_VERSION: str = "0.0.1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_ANON_KEY: str | None = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_SERVICE_ROLE_KEY: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    # CORS settings
    def get_cors_origins(self) -> list[str]:
        if self.ENVIRONMENT == "production":
            return [
                "https://deepcuts.casa",
                "https://deepcuts.onrender.com",
            ]
        return [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001"
        ]

settings = Settings()
