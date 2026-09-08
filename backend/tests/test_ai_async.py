from types import SimpleNamespace

import anthropic
import httpx

from app.services.ai import AIService

RECOMMENDATION_XML = """
<recommendations>
<album>
<title>Journey in Satchidananda</title>
<artist>Alice Coltrane</artist>
<year>1971</year>
<genre>spiritual jazz</genre>
<explanation>Modal harp and saxophone arrangements create a meditative ensemble sound.</explanation>
</album>
</recommendations>
"""


class FakeGeminiClient:
    def __init__(self) -> None:
        self.awaited = False

    async def generate_content_async(self, _prompt: str, **_kwargs):
        self.awaited = True
        return SimpleNamespace(text=RECOMMENDATION_XML)


class FakeClaudeMessages:
    def __init__(self) -> None:
        self.awaited = False

    async def create(self, **_kwargs):
        self.awaited = True
        content = [SimpleNamespace(text=RECOMMENDATION_XML)]
        return SimpleNamespace(content=content)


class FailingClaudeMessages:
    def __init__(self) -> None:
        self.calls = 0

    async def create(self, **_kwargs):
        self.calls += 1
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        response = httpx.Response(400, request=request)
        raise anthropic.BadRequestError(
            "credit balance is too low",
            response=response,
            body={"error": {"type": "invalid_request_error"}},
        )


async def test_gemini_recommendation_call_is_awaited():
    service = object.__new__(AIService)
    service.ACTIVE_MODEL = "gemini-2.5-flash"
    service.gemini_client = FakeGeminiClient()

    result = await service.get_album_recommendations("A Love Supreme")

    assert service.gemini_client.awaited is True
    assert result.albums[0].title == "Journey in Satchidananda"


async def test_claude_recommendation_call_is_awaited():
    service = object.__new__(AIService)
    service.ACTIVE_MODEL = "claude-sonnet-4-5-20250929"
    messages = FakeClaudeMessages()
    service.claude_client = SimpleNamespace(messages=messages)
    service._fallback_until = 0.0

    result = await service.get_album_recommendations("A Love Supreme")

    assert messages.awaited is True
    assert result.albums[0].artist == "Alice Coltrane"


async def test_claude_credit_failure_falls_back_to_gemini(monkeypatch):
    service = object.__new__(AIService)
    service.ACTIVE_MODEL = "claude-sonnet-4-5-20250929"
    messages = FailingClaudeMessages()
    service.claude_client = SimpleNamespace(messages=messages)
    service.claude_configured = True
    service.gemini_client = FakeGeminiClient()
    service.gemini_configured = True
    service._fallback_until = 0.0
    monkeypatch.setenv("ACTIVE_MODEL", service.ACTIVE_MODEL)
    monkeypatch.setattr(service, "_init_clients", lambda: None)

    result = await service.get_album_recommendations("A Love Supreme")

    assert result.albums[0].title == "Journey in Satchidananda"
    assert service.ACTIVE_MODEL == "claude-sonnet-4-5-20250929"
    assert messages.calls == 1


async def test_open_fallback_circuit_skips_anthropic(monkeypatch):
    service = object.__new__(AIService)
    service.ACTIVE_MODEL = "claude-sonnet-4-5-20250929"
    messages = FailingClaudeMessages()
    service.claude_client = SimpleNamespace(messages=messages)
    service.claude_configured = True
    service.gemini_client = FakeGeminiClient()
    service.gemini_configured = True
    service._fallback_until = float("inf")
    monkeypatch.setattr(service, "_init_clients", lambda: None)

    result = await service.get_album_recommendations("A Love Supreme")

    assert result.albums[0].title == "Journey in Satchidananda"
    assert messages.calls == 0
