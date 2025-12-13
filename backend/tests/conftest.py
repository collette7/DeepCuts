import os

import pytest
from dotenv import load_dotenv

load_dotenv()


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
