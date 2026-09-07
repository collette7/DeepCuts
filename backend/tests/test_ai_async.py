from types import SimpleNamespace

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

    async def generate_content_async(self, _prompt: str):
        self.awaited = True
        return SimpleNamespace(text=RECOMMENDATION_XML)


class FakeClaudeMessages:
    def __init__(self) -> None:
        self.awaited = False

    async def create(self, **_kwargs):
        self.awaited = True
        content = [SimpleNamespace(text=RECOMMENDATION_XML)]
        return SimpleNamespace(content=content)


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

    result = await service.get_album_recommendations("A Love Supreme")

    assert messages.awaited is True
    assert result.albums[0].artist == "Alice Coltrane"
