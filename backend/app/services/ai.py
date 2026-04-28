import logging
import os
import re
import uuid
from typing import Any

import anthropic

from app.models.albums import AlbumData

logger = logging.getLogger('deepcuts')

# Known valid models - update these when providers deprecate/add models
# Source: https://docs.anthropic.com/en/docs/about-claude/models/overview
VALID_CLAUDE_MODELS = [
    # Claude 4.5 (Latest - 2025)
    {"id": "claude-opus-4-5-20251101", "name": "Claude Opus 4.5", "retirement": "2026-11-24", "free": False},
    {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5", "retirement": "2026-09-29", "free": False},
    {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "retirement": "2026-10-15", "free": False},
    # Claude 4.1
    {"id": "claude-opus-4-1-20250805", "name": "Claude Opus 4.1", "retirement": "2026-08-05", "free": False},
    # Claude 4
    {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "retirement": "2026-05-14", "free": False},
    {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "retirement": "2026-05-14", "free": False},
    # Claude 3.5
    {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "retirement": "2025-10-22", "free": False},
    # Claude 3 (Legacy)
    {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "retirement": "2025-03-07", "free": False},
]

# Source: https://ai.google.dev/gemini-api/docs/models
VALID_GEMINI_MODELS = [
    # Gemini 3 (Preview)
    {"id": "gemini-3-pro-preview", "name": "Gemini 3 Pro (Preview)", "free": True},
    # Gemini 2.5
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "free": True},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "free": True},
    {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "free": True},
    # Gemini 2.0
    {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "free": True},
    {"id": "gemini-2.0-flash-lite", "name": "Gemini 2.0 Flash Lite", "free": True},
]

# Deprecated models that will cause errors
DEPRECATED_MODELS = [
    "gemini-1.5-flash",  # Use gemini-2.0-flash
    "gemini-1.5-pro",  # Use gemini-2.5-pro
    "gemini-pro",  # Use gemini-2.5-pro
    "claude-3-opus-20240229",  # Deprecated June 30, 2025, retiring Jan 5, 2026
    "claude-3-7-sonnet-20250219",  # Deprecated Oct 28, 2025, retiring Feb 19, 2026
    "claude-3-haiku-20240307",  # Retired March 7, 2025
    "claude-3-5-haiku-20241022",  # Retired October 22, 2025
    "claude-2",
    "claude-2.1",
    "claude-instant-1.2",
]

def get_all_valid_model_ids():
    """Get list of all valid model IDs."""
    claude_ids = [m["id"] for m in VALID_CLAUDE_MODELS]
    gemini_ids = [m["id"] for m in VALID_GEMINI_MODELS]
    return claude_ids + gemini_ids

def get_model_info(model_id: str) -> dict[str, Any] | None:
    """Get info about a specific model."""
    for m in VALID_CLAUDE_MODELS + VALID_GEMINI_MODELS:
        if m["id"] == model_id:
            return m
    return None


class AIService:
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        self._model_cache = None
        self._cache_time = None
        self._cache_ttl = 60  # Cache for 60 seconds

        # Get initial model from env or Supabase
        self.ACTIVE_MODEL = self._get_active_model()
        self.model_validated = False
        self.validation_error = None

        # Validate model on startup
        self._validate_model_config()

        # Initialize clients (both, so we can switch at runtime)
        self._init_clients()

        logger.info(f"AI Service initialized with model: {self.ACTIVE_MODEL}")

    def _init_clients(self):
        """Initialize AI provider clients."""
        import google.generativeai as genai

        # Initialize Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_configured = True
        else:
            self.gemini_configured = False

        # Initialize Claude
        claude_key = os.getenv("CLAUDE_API_KEY")
        if claude_key:
            self.claude_client = anthropic.Anthropic(api_key=claude_key)
            self.claude_configured = True
        else:
            self.claude_configured = False

    def _get_active_model(self) -> str:
        """Get active model from Supabase settings or fall back to env var."""
        import time

        # Check cache first
        if self._model_cache and self._cache_time:
            if time.time() - self._cache_time < self._cache_ttl:
                return self._model_cache

        # Try to get from Supabase
        if self.supabase:
            try:
                result = self.supabase.table('app_settings').select('value').eq('key', 'active_model').single().execute()
                if result.data and result.data.get('value'):
                    self._model_cache = result.data['value']
                    self._cache_time = time.time()
                    return self._model_cache
            except Exception as e:
                logger.debug(f"Could not get model from Supabase: {e}")

        # Fall back to env var
        return os.getenv("ACTIVE_MODEL", "claude-sonnet-4-5-20250929")

    def refresh_model(self):
        """Refresh the active model from config (call this to pick up changes)."""
        self._model_cache = None
        self._cache_time = None
        new_model = self._get_active_model()
        if new_model != self.ACTIVE_MODEL:
            logger.info(f"Switching model from {self.ACTIVE_MODEL} to {new_model}")
            self.ACTIVE_MODEL = new_model
            self._validate_model_config()
        return self.ACTIVE_MODEL

    @property
    def is_gemini(self) -> bool:
        """Check if current model is Gemini."""
        return "gemini" in self.ACTIVE_MODEL.lower()

    @property
    def client(self):
        """Get the appropriate client for the current model."""
        if self.is_gemini:
            import google.generativeai as genai
            return genai.GenerativeModel(self.ACTIVE_MODEL)
        return self.claude_client

    def _validate_model_config(self):
        """Validate the configured model on startup."""
        # Check for deprecated models
        if self.ACTIVE_MODEL in DEPRECATED_MODELS:
            self.validation_error = (
                f"CRITICAL: Model '{self.ACTIVE_MODEL}' is DEPRECATED and will not work! "
                f"Update to a valid model from the settings."
            )
            logger.error(self.validation_error)
            return

        # Check if model is in known valid list
        all_valid_ids = get_all_valid_model_ids()
        if self.ACTIVE_MODEL not in all_valid_ids:
            logger.warning(
                f"Model '{self.ACTIVE_MODEL}' not in known valid models list. "
                f"This may work if it's a new model, but verify it exists."
            )
        else:
            self.model_validated = True
            logger.info(f"Model '{self.ACTIVE_MODEL}' validated successfully")

    @property
    def is_ready(self) -> bool:
        if self.ACTIVE_MODEL in DEPRECATED_MODELS:
            return False
        if self.is_gemini:
            return self.gemini_configured
        return self.claude_configured

    def get_ready_error(self) -> str | None:
        if self.ACTIVE_MODEL in DEPRECATED_MODELS:
            return (
                f"Model '{self.ACTIVE_MODEL}' is deprecated and no longer available. "
                f"Switch to a current model via /api/v1/settings/models."
            )
        if self.is_gemini and not self.gemini_configured:
            return "Gemini API key not configured. Set GEMINI_API_KEY environment variable."
        if not self.is_gemini and not self.claude_configured:
            return "Claude API key not configured. Set CLAUDE_API_KEY environment variable."
        return None

    async def verify_model_exists(self) -> dict[str, Any]:
        """Make a test API call to verify the model exists and is accessible."""
        result = {
            "model": self.ACTIVE_MODEL,
            "provider": "gemini" if self.is_gemini else "claude",
            "valid": False,
            "error": None
        }

        try:
            if self.is_gemini:
                response = self.client.generate_content("test")
                result["valid"] = response.text is not None
            else:
                message = self.client.messages.create(
                    model=self.ACTIVE_MODEL,
                    max_tokens=5,
                    messages=[{"role": "user", "content": "test"}]
                )
                result["valid"] = message.content is not None
        except Exception as e:
            result["error"] = str(e)
            if "not found" in str(e).lower() or "404" in str(e):
                result["error"] = f"Model '{self.ACTIVE_MODEL}' not found. Update to a valid model."

        return result

    def get_config_status(self) -> dict[str, Any]:
        """Get the current AI configuration status for health checks."""
        model_info = get_model_info(self.ACTIVE_MODEL)
        return {
            "active_model": self.ACTIVE_MODEL,
            "model_name": model_info["name"] if model_info else self.ACTIVE_MODEL,
            "provider": "gemini" if self.is_gemini else "claude",
            "model_validated": self.model_validated,
            "validation_error": self.validation_error,
            "is_deprecated": self.ACTIVE_MODEL in DEPRECATED_MODELS,
            "is_free": model_info["free"] if model_info else False,
            "available_models": {
                "claude": VALID_CLAUDE_MODELS,
                "gemini": VALID_GEMINI_MODELS,
            },
        }

    def get_recommendation_prompt(self, album_name: str) -> str:
        """Prompt template for album recommendations."""
        return f"""You are an expert music recommender. Recommend 10 real albums similar to the one below, focusing on deep cuts and overlooked records.

CRITICAL RULES:
- Return the ORIGINAL album title as released, do NOT translate non-English titles to English
- If the original title is Japanese, return it in Japanese
- If the original title is English, return it in English
- Do NOT mix translations - pick the original release language
- Only recommend full-length studio albums (LPs), NOT singles or EPs
- Focus on hidden gems and lesser-known releases
- Emphasize musical similarities over superficial genre categorization
- Be specific about genres and subgenres
- Provide specific, concrete details rather than vague descriptions

<input_album>
{album_name}
</input_album>

Present your final recommendations in <recommendations> tags using this exact XML structure:

<recommendations>
  <album>
    <title>[Album Name]</title>
    <artist>[Artist Name]</artist>
    <year>[Release Year]</year>
    <genre>[Specific genre/subgenre]</genre>
    <mood>[Primary mood or atmosphere]</mood>
    <explanation>[2-3 sentences focusing on specific musical qualities and characteristics that connect this album to the input. Mention concrete elements like production techniques, instrumentation, mood, or structural similarities.]</explanation>
  </album>
  <!-- Continue this structure for all 10 albums -->
</recommendations>"""

    def parse_recommendations(self, response_text: str) -> list[AlbumData]:
        """Parse the XML"""
        recommendations = []

        recommendations_match = re.search(r'<recommendations>(.*?)</recommendations>', response_text, re.DOTALL)
        if not recommendations_match:
            logger.warning("No <recommendations> tag found in AI response")
            logger.debug(f"Looking for recommendations in response: {response_text[:1000]}")
            return recommendations

        recommendations_xml = recommendations_match.group(1)
        logger.debug(f"Found recommendations XML section with {len(recommendations_xml)} chars")

        # Parse each album rec - supports both old format (without mood) and new format (with mood)
        album_pattern = r'<album>\s*<title>(.*?)</title>\s*<artist>(.*?)</artist>\s*<year>(.*?)</year>\s*<genre>(.*?)</genre>(?:\s*<mood>(.*?)</mood>)?\s*<explanation>(.*?)</explanation>\s*</album>'
        album_matches = re.findall(album_pattern, recommendations_xml, re.DOTALL)
        logger.info(f"Found {len(album_matches)} album matches in XML")

        for match in album_matches:
            try:
                # Handle both formats - with and without mood tag
                if len(match) == 5:
                    title, artist, year, genre, explanation = match
                    mood = ""
                elif len(match) == 6:
                    title, artist, year, genre, mood, explanation = match
                else:
                    logger.warning(f"Unexpected match format with {len(match)} groups: {match}")
                    continue

                # Clean up
                title = title.strip()
                artist = artist.strip()
                year_str = year.strip()
                genre = genre.strip()
                explanation = explanation.strip()

                # Parse year
                try:
                    parsed_year = int(year_str) if year_str.isdigit() else None
                except ValueError:
                    parsed_year = None

                album = AlbumData(
                    id=str(uuid.uuid4()),
                    title=title,
                    artist=artist,
                    year=parsed_year,
                    genre=genre,
                    spotify_preview_url=None,
                    spotify_url=None,
                    discogs_url=None,
                    cover_url=None,
                    reasoning=explanation
                )
                recommendations.append(album)

            except Exception as e:
                logger.error(f"Error parsing album: {e}")
                continue

        return recommendations

    async def get_album_recommendations(self, album_name: str, feedback: str = "") -> list[AlbumData]:
        try:
            prompt = self.get_recommendation_prompt(album_name)
            
            if feedback:
                prompt += f"\n\n{feedback}"

            if self.is_gemini:
                response = self.client.generate_content(prompt)
                response_text = response.text
            else:
                message = self.client.messages.create(
                    model=self.ACTIVE_MODEL,
                    max_tokens=16384,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                response_text = message.content[0].text

            logger.debug(f"AI Response (first 500 chars): {response_text[:500]}")

            recommendations = self.parse_recommendations(response_text)
            logger.info(f"Parsed {len(recommendations)} recommendations from AI response")

            return recommendations

        except Exception as e:
            logger.error(f"Error getting recommendations from AI: {e}", exc_info=True)
            return []


async def set_active_model(supabase_client, model_id: str) -> dict[str, Any]:
    """Set the active model in Supabase settings."""
    # Validate model
    if model_id in DEPRECATED_MODELS:
        return {"success": False, "error": f"Model '{model_id}' is deprecated"}

    all_valid = get_all_valid_model_ids()
    if model_id not in all_valid:
        return {"success": False, "error": f"Model '{model_id}' is not in the known valid models list"}

    try:
        # Upsert the setting
        supabase_client.table('app_settings').upsert({
            "key": "active_model",
            "value": model_id,
        }, on_conflict="key").execute()

        # Refresh the AI service model
        ai_service.supabase = supabase_client
        ai_service.refresh_model()

        model_info = get_model_info(model_id)
        return {
            "success": True,
            "model_id": model_id,
            "model_name": model_info["name"] if model_info else model_id,
            "is_free": model_info["free"] if model_info else False,
        }
    except Exception as e:
        logger.error(f"Error setting active model: {e}")
        return {"success": False, "error": str(e)}


# Initialize AI service (Supabase client will be set later via main.py)
ai_service = AIService()
