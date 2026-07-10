import os

import pytest
from dotenv import load_dotenv

load_dotenv()

# app.config.Settings reads these at import time (module-level singleton), so
# they must be set before ANY test module imports app.config transitively —
# conftest.py is guaranteed to load before test module collection, regardless
# of alphabetical file order.
os.environ.setdefault("SUPABASE_URL", "http://test.invalid")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-service-key")
os.environ.setdefault("ACTIVE_MODEL", "claude-haiku-4-5-20251001")


@pytest.fixture
def claude_api_key():
    """Get Claude API key from environment."""
    key = os.getenv("CLAUDE_API_KEY")
    if not key:
        pytest.skip("CLAUDE_API_KEY not set")
    return key


@pytest.fixture
def gemini_api_key():
    """Get Gemini API key from environment."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        pytest.skip("GEMINI_API_KEY not set")
    return key
