"""
Tests to validate AI model configurations and API connectivity.

These tests ensure that:
1. Configured model names are valid and supported
2. API keys are properly configured
3. APIs are accessible and responding

Run with: pytest tests/test_ai_models.py -v
Run specific test: pytest tests/test_ai_models.py::test_claude_model_exists -v
"""

import os

import anthropic
import google.generativeai as genai
import pytest

# Known valid model names
VALID_CLAUDE_MODELS = [
    # Claude 4.5 (Latest - 2025)
    "claude-sonnet-4-5-20250929",
    "claude-opus-4-5-20251101",
    "claude-haiku-4-5-20251001",
    # Claude 3.5
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    # Claude 3 Haiku
    "claude-3-haiku-20240307",
]

VALID_GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

# Deprecated/invalid models
DEPRECATED_MODELS = [
    "gemini-1.5-flash",  # Deprecated
    "gemini-1.5-pro",  # Deprecated
    "gemini-pro",  # Old name
    "claude-2",  # Deprecated
    "claude-2.1",  # Deprecated
    "claude-instant-1.2",  # Deprecated
    "claude-3-opus-20240229",  # Deprecated
]


class TestModelConfiguration:
    """Test that configured models are valid."""

    def test_active_model_not_deprecated(self):
        """Ensure ACTIVE_MODEL is not set to a known deprecated model."""
        active_model = os.getenv("ACTIVE_MODEL", "claude-3-5-sonnet-20241022")

        assert active_model not in DEPRECATED_MODELS, (
            f"ACTIVE_MODEL '{active_model}' is deprecated! "
            f"Use one of: {VALID_CLAUDE_MODELS[:3]} (Claude) or {VALID_GEMINI_MODELS[:3]} (Gemini)"
        )

    def test_active_model_is_known_valid(self):
        """Warn if ACTIVE_MODEL is not in our known valid list."""
        active_model = os.getenv("ACTIVE_MODEL", "claude-3-5-sonnet-20241022")
        all_valid = VALID_CLAUDE_MODELS + VALID_GEMINI_MODELS

        if active_model not in all_valid:
            pytest.warns(
                UserWarning,
                match=f"Model '{active_model}' not in known valid models list"
            )


class TestClaudeAPI:
    """Test Claude/Anthropic API connectivity and model availability."""

    def test_claude_api_key_configured(self):
        """Ensure Claude API key is set."""
        key = os.getenv("CLAUDE_API_KEY")
        assert key is not None, "CLAUDE_API_KEY environment variable not set"
        assert len(key) > 20, "CLAUDE_API_KEY appears to be invalid (too short)"
        assert key.startswith("sk-ant-"), f"CLAUDE_API_KEY should start with 'sk-ant-', got: {key[:10]}..."

    def test_claude_model_exists(self, claude_api_key):
        """Verify the configured Claude model exists and is accessible."""
        active_model = os.getenv("ACTIVE_MODEL", "claude-3-5-sonnet-20241022")

        # Skip if not using Claude
        if "gemini" in active_model.lower():
            pytest.skip("ACTIVE_MODEL is set to Gemini, skipping Claude test")

        client = anthropic.Anthropic(api_key=claude_api_key)

        try:
            # Make a minimal API call to verify the model exists
            response = client.messages.create(
                model=active_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            assert response.content is not None
        except anthropic.NotFoundError as e:
            pytest.fail(
                f"Claude model '{active_model}' not found! "
                f"Valid models: {VALID_CLAUDE_MODELS}. Error: {e}"
            )
        except anthropic.AuthenticationError as e:
            pytest.fail(f"Claude API authentication failed. Check CLAUDE_API_KEY. Error: {e}")

    @pytest.mark.parametrize("model", ["claude-3-haiku-20240307"])  # Test only models accessible with our API key
    def test_claude_known_models_accessible(self, claude_api_key, model):
        """Verify known Claude models are still accessible."""
        client = anthropic.Anthropic(api_key=claude_api_key)

        try:
            response = client.messages.create(
                model=model,
                max_tokens=5,
                messages=[{"role": "user", "content": "test"}]
            )
            assert response.content is not None
        except anthropic.NotFoundError:
            pytest.fail(f"Claude model '{model}' is no longer available - update VALID_CLAUDE_MODELS")
        except anthropic.PermissionDeniedError:
            pytest.skip(f"Claude model '{model}' not accessible with current API key")


class TestGeminiAPI:
    """Test Google Gemini API connectivity and model availability."""

    def test_gemini_api_key_configured(self):
        """Ensure Gemini API key is set."""
        key = os.getenv("GEMINI_API_KEY")
        assert key is not None, "GEMINI_API_KEY environment variable not set"
        assert len(key) > 20, "GEMINI_API_KEY appears to be invalid (too short)"

    def test_gemini_model_exists(self, gemini_api_key):
        """Verify the configured Gemini model exists and is accessible."""
        active_model = os.getenv("ACTIVE_MODEL", "claude-3-5-sonnet-20241022")

        # Skip if not using Gemini
        if "gemini" not in active_model.lower():
            pytest.skip("ACTIVE_MODEL is set to Claude, skipping Gemini test")

        genai.configure(api_key=gemini_api_key)

        try:
            model = genai.GenerativeModel(active_model)
            response = model.generate_content("Hi")
            assert response.text is not None
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                pytest.fail(
                    f"Gemini model '{active_model}' not found! "
                    f"Valid models: {VALID_GEMINI_MODELS}. Error: {e}"
                )
            raise

    def test_gemini_list_available_models(self, gemini_api_key):
        """List available Gemini models for reference."""
        genai.configure(api_key=gemini_api_key)

        try:
            models = list(genai.list_models())

            # Just verify we can list models - this helps debug which models are available
            assert len(models) > 0, "No models found"
            print(f"\nAvailable Gemini models: {[m.name for m in models[:10]]}")

        except Exception as e:
            pytest.fail(f"Failed to list Gemini models: {e}")

    @pytest.mark.parametrize("model", ["gemini-2.5-flash"])  # Test one stable model to avoid rate limits
    def test_gemini_known_models_accessible(self, gemini_api_key, model):
        """Verify known Gemini models are still accessible."""
        genai.configure(api_key=gemini_api_key)

        try:
            gen_model = genai.GenerativeModel(model)
            response = gen_model.generate_content("test")
            assert response.text is not None
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "404" in error_str:
                pytest.fail(f"Gemini model '{model}' is no longer available - update VALID_GEMINI_MODELS. Error: {e}")
            if "429" in str(e) or "rate" in error_str or "quota" in error_str:
                pytest.skip(f"Gemini rate limited - skipping test. Error: {e}")
            raise


class TestDeprecatedModels:
    """Ensure deprecated models are not being used."""

    @pytest.mark.parametrize("deprecated_model", DEPRECATED_MODELS)
    def test_deprecated_model_not_configured(self, deprecated_model):
        """Fail if ACTIVE_MODEL is set to a deprecated model."""
        active_model = os.getenv("ACTIVE_MODEL", "claude-3-5-sonnet-20241022")

        assert active_model != deprecated_model, (
            f"ACTIVE_MODEL is set to deprecated model '{deprecated_model}'! "
            f"This model may not work. Please update to a supported model."
        )
