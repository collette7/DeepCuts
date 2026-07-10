import os

from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "DeepCuts"
    PROJECT_VERSION: str = "0.0.1"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    POCKETBASE_URL: str | None = os.getenv("POCKETBASE_URL")
    POCKETBASE_ADMIN_EMAIL: str | None = os.getenv("POCKETBASE_ADMIN_EMAIL")
    POCKETBASE_ADMIN_PASSWORD: str | None = os.getenv("POCKETBASE_ADMIN_PASSWORD")

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
