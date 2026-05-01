import logging
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any

import anthropic

from app.models.albums import AlbumData
from app.services.render_api import update_render_env_var

logger = logging.getLogger('deepcuts')


@dataclass
class RecommendationResult:
    albums: list[AlbumData]
    raw_response: str

# Known valid models - update these when providers deprecate/add models
# Source: https://docs.anthropic.com/en/docs/about-claude/models/overview
VALID_CLAUDE_MODELS = [
    # Claude 4.7 (Latest)
    {"id": "claude-opus-4-7", "name": "Claude Opus 4.7", "retirement": "2027-04-16", "free": False},
    # Claude 4.6
    {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "retirement": "2027-02-05", "free": False},
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "retirement": "2027-02-17", "free": False},
    # Claude 4.5
    {"id": "claude-opus-4-5-20251101", "name": "Claude Opus 4.5", "retirement": "2026-11-24", "free": False},
    {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5", "retirement": "2026-09-29", "free": False},
    {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "retirement": "2026-10-15", "free": False},
    # Claude 4.1
    {"id": "claude-opus-4-1-20250805", "name": "Claude Opus 4.1", "retirement": "2026-08-05", "free": False},
]

# Source: https://ai.google.dev/gemini-api/docs/models
VALID_GEMINI_MODELS = [
    # Gemini 3.1 (Latest)
    {"id": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro Preview", "free": True},
    {"id": "gemini-3-flash-preview", "name": "Gemini 3 Flash Preview", "free": True},
    {"id": "gemini-3.1-flash-lite-preview", "name": "Gemini 3.1 Flash Lite Preview", "free": True},
    # Gemini 2.5
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "free": True},
    {"id": "gemini-2.5-pro-preview", "name": "Gemini 2.5 Pro Preview", "free": True},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "free": True},
    {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "free": True},
]

# Deprecated models that will cause errors
DEPRECATED_MODELS = [
    "gemini-3-pro-preview",  # Shut down March 9, 2026; use gemini-3.1-pro-preview
    "gemini-2.0-flash",  # Shutting down June 1, 2026
    "gemini-2.0-flash-lite",  # Shutting down June 1, 2026
    "gemini-2.5-flash-preview-09-25",  # Already shut down
    "gemini-1.5-flash",  # Use gemini-2.5-flash
    "gemini-1.5-pro",  # Use gemini-2.5-pro
    "gemini-pro",  # Use gemini-2.5-pro
    "claude-opus-4-20250514",  # Deprecated April 14, 2026; retiring June 15, 2026
    "claude-sonnet-4-20250514",  # Deprecated April 14, 2026; retiring June 15, 2026
    "claude-3-opus-20240229",  # Retired January 5, 2026
    "claude-3-7-sonnet-20250219",  # Retired February 19, 2026
    "claude-3-haiku-20240307",  # Retired April 20, 2026
    "claude-3-5-haiku-20241022",  # Retired February 19, 2026
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
    def __init__(self):
        self.ACTIVE_MODEL = os.getenv("ACTIVE_MODEL", "claude-sonnet-4-5-20250929")
        self.model_validated = False
        self.validation_error = None

        self._validate_model_config()
        self._init_clients()

        logger.info(f"AI Service initialized with model: {self.ACTIVE_MODEL}")

    def _init_clients(self):
        import google.generativeai as genai

        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini_configured = True
        else:
            self.gemini_configured = False

        claude_key = os.getenv("CLAUDE_API_KEY")
        if claude_key:
            self.claude_client = anthropic.Anthropic(api_key=claude_key)
            self.claude_configured = True
        else:
            self.claude_configured = False

    def refresh_model(self):
        new_model = os.getenv("ACTIVE_MODEL", "claude-sonnet-4-5-20250929")
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

    async def find_working_model(self) -> dict[str, Any]:
        candidates = []
        if self.gemini_configured:
            candidates.extend([m["id"] for m in VALID_GEMINI_MODELS])
        if self.claude_configured:
            candidates.extend([m["id"] for m in VALID_CLAUDE_MODELS])
        for model_id in candidates:
            if model_id in DEPRECATED_MODELS:
                continue
            original = self.ACTIVE_MODEL
            self.ACTIVE_MODEL = model_id
            try:
                result = await self.verify_model_exists()
                if result["valid"]:
                    self.ACTIVE_MODEL = model_id
                    self._validate_model_config()
                    os.environ["ACTIVE_MODEL"] = model_id
                    persist = await update_render_env_var("ACTIVE_MODEL", model_id)
                    if not persist["success"]:
                        logger.warning(f"Working model {model_id} found but failed to persist to Render: {persist.get('error')}")
                    return {
                        "success": True,
                        "model_id": model_id,
                        "model_name": get_model_info(model_id)["name"] if get_model_info(model_id) else model_id,
                        "persisted": persist.get("success", False),
                    }
            finally:
                if self.ACTIVE_MODEL != model_id:
                    self.ACTIVE_MODEL = original
        return {"success": False, "error": "No configured models responded successfully"}

    def get_recommendation_prompt(self, album_name: str) -> str:
        """Prompt template for album recommendations."""
        return f"""You are an expert music recommender with deep knowledge of albums across
    genres, eras, and regional scenes. Your job: recommend releases similar to
    a given input album, prioritizing deeper cuts, overlooked records, and
    side projects by related producers.

    <input_album>
    {album_name}
    </input_album>

    ==================================================================
    HARD CONSTRAINTS — read these before doing anything else
    ==================================================================

    1. EXISTENCE CHECK (most important rule)
       Every release you recommend MUST be real and released. You will assign
       a numeric existence-confidence score (1-10) to every candidate, and
       only candidates scoring 8 or higher may appear in the final output.

       Common failure modes to avoid:
       - Inventing plausible-sounding titles in genres where your knowledge
         is thin (South African house, amapiano, regional African scenes,
         niche Japanese releases, recent underground releases)
       - Confusing labels or collectives with artists ("Hyperdub" is a label,
         not an artist; "Brainfeeder" is a label)
       - Mis-titling real albums by inserting or swapping words
       - Attributing real albums to the wrong artist
       - Recommending post-cutoff albums you have not seen confirmed

       When in doubt, replace an uncertain pick with an older, well-documented
       release you are certain about. A correct boring pick beats a fabricated
       exciting one.

    2. NO SINGLES. LPs, EPs, and mixtapes are all acceptable.

    3. PRESERVE ORIGINAL TITLE LANGUAGE
       Use the title as originally released. Do not translate Japanese,
       Portuguese, French, Zulu, etc. titles into English.

    4. SPECIFIC GENRES
       Never use bare "pop", "rock", "jazz", "electronic", "hip hop", or "r&b".
       Use precise subgenre labels: "amapiano", "broken beat", "spiritual
       jazz", "city pop", "deep house", "gqom", "Afro-tech", "kwaito",
       "UK bass", "shoegaze", "post-punk", etc.

    ==================================================================
    PROCESS
    ==================================================================

    Step 1 — Analyze the input album
    In <album_analysis> tags:
      a) State the album's artist, year, label, and primary scene/region.
         Assign your existence confidence for the INPUT album (1-10). If
         below 8, say so and stop — do not invent recommendations for an
         album you cannot verify.
      b) Rate each of the following 1-10 for how central it is to the
         album's identity, with a one-line concrete example from the record:
           - Mood/atmosphere
           - Production style (analog/digital, lo-fi/hi-fi, dry/reverb-soaked)
           - Rhythmic character (BPM range, swing, polyrhythm, log drum, etc.)
           - Instrumentation and timbre
           - Vocal treatment (if any)
           - Structural/arrangement tendencies (track length, builds, repetition)
           - Regional/scene influence (specific: "Pretoria amapiano",
             "Detroit second-wave techno", "Bristol post-trip-hop")
           - Genre fusions or unusual elements

    Step 2 — Generate candidates with confidence scoring
    In <recommendation_search> tags:
      a) Build a similarity rubric weighted by the importance ratings above.
      b) Propose 18-25 candidate releases. For EACH candidate, output exactly:

         Title | Artist | Year | Label | Format (LP / EP / mixtape)
         Existence confidence: N/10
         Evidence: <one specific fact anchoring this release in your knowledge —
           e.g., "follow-up to <prior album>, released on <label>",
           "produced by <name>, features <track>", "won <award> in <year>".
           Vague evidence ("I've heard of this") caps confidence at 7.>
         Similarity score: N/10
         Similarity reasoning: <one sentence>

      c) Calibration guide for existence confidence:
           10    = Canonical release you can describe in detail (specific
                   tracks, production credits, reception)
           8-9   = Confident: you know the artist's discography well and
                   this release fits, with at least one specific anchoring fact
           6-7   = Probable but hazy: you recognize artist + general era
                   but cannot cite specifics. NOT ELIGIBLE for final list.
           3-5   = Plausible guess based on pattern-matching scene
                   conventions. NOT ELIGIBLE.
           1-2   = Likely fabricated. NOT ELIGIBLE.

         Be honest. It is better to score yourself a 7 and drop the pick
         than to inflate to 9 and ship a fabrication.

      d) Drop every candidate scoring below 8 on existence. If this leaves
         fewer than 10, generate more candidates until you have 10 that all
         score 8+. Do not lower the threshold.

      e) Verify each survivor is musically similar to the input, not just
         superficially adjacent (shared label, scene, or collaborator does
         not by itself mean musically similar).

    Step 3 — Output the final 10
    Use exactly this format. No commentary outside the tags.

    <recommendations>
    <album>
        <title>Real Release Title</title>
        <artist>Real Artist Name</artist>
        <year>YYYY</year>
        <genre>Specific subgenre</genre>
        <explanation>2 sentences citing concrete shared musical traits —
        name production techniques, instrumentation, rhythmic feel, or
        arrangement choices. Do NOT use the words "similar", "like",
        "same vibe", or "feels like".</explanation>
    </album>
    ... (10 total)
    </recommendations>

    ==================================================================
    SELF-CHECK BEFORE RETURNING
    ==================================================================

    [ ] All 10 entries scored 8+ on existence confidence
    [ ] No labels or collectives listed as artists
    [ ] No translated titles
    [ ] No generic single-word genres
    [ ] At least 8 distinct artists across the 10 picks
    [ ] Year range spans more than 5 years
    [ ] Each explanation names concrete musical details, not vibes
    [ ] No explanation contains "similar", "like", "same", "vibe", "feels like"

    If any check fails, fix it before returning."""

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

    async def get_album_recommendations(self, album_name: str, feedback: str = "") -> RecommendationResult:
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

            return RecommendationResult(albums=recommendations, raw_response=response_text)

        except Exception as e:
            logger.error(f"Error getting recommendations from AI: {e}", exc_info=True)
            return RecommendationResult(albums=[], raw_response="")


async def set_active_model(model_id: str) -> dict[str, Any]:
    if model_id in DEPRECATED_MODELS:
        return {"success": False, "error": f"Model '{model_id}' is deprecated"}

    all_valid = get_all_valid_model_ids()
    if model_id not in all_valid:
        return {"success": False, "error": f"Model '{model_id}' is not in the known valid models list"}

    try:
        os.environ["ACTIVE_MODEL"] = model_id
        ai_service.refresh_model()
        persist = await update_render_env_var("ACTIVE_MODEL", model_id)

        model_info = get_model_info(model_id)
        return {
            "success": True,
            "model_id": model_id,
            "model_name": model_info["name"] if model_info else model_id,
            "is_free": model_info["free"] if model_info else False,
            "persisted": persist.get("success", False),
        }
    except Exception as e:
        logger.error(f"Error setting active model: {e}")
        return {"success": False, "error": str(e)}


# Initialize AI service (Supabase client will be set later via main.py)
ai_service = AIService()
