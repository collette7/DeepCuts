# Plan 001: Use async SDK clients for AI calls so the event loop stops blocking

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md` — unless a reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**: `git diff --stat d9c8a91..HEAD -- backend/app/services/ai.py backend/requirements.txt`
> If any in-scope file changed since this plan was written, compare the "Current state" excerpts against the live code before proceeding; on a mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: perf
- **Planned at**: commit `d9c8a91`, 2026-06-18

## Why this matters

The Claude SDK is initialized as `anthropic.Anthropic(...)` (synchronous) and called as `self.client.messages.create(...)` from inside an `async def`. Gemini is the same: `self.client.generate_content(...)` is sync. Every AI call (1–15 s, up to 3 retries inside one search) blocks the entire event loop, which freezes every other endpoint on this process (favorites, autocomplete, health checks, settings reads) until the AI returns. Switching to the SDKs' async siblings is a small, mechanical change that removes the blocking property entirely — the request that pays the AI's latency stops penalizing every concurrent request.

## Current state

**Repository layout (relevant subset)**

- `backend/app/services/ai.py` — `AIService` class; constructs clients, makes AI calls.
- `backend/app/main.py` — FastAPI app; calls `ai_service.get_album_recommendations(...)` from `search_albums` (line 738) and `ai_service.verify_model_exists()` from a health endpoint.
- `backend/requirements.txt` — pinned deps: `anthropic==0.40.0`, `google-generativeai==0.8.3`.

**Conventions** (match these):

- FastAPI handlers are `async def` and `await` IO. See `backend/app/main.py:585-684` for the existing `async def verify_album_exists(...)` that already uses `async with httpx.AsyncClient()` correctly.
- Logging: `logger = logging.getLogger('deepcuts')` at top of file; use `logger.info`/`logger.error`, not `print`.
- Errors in AI service log and return an empty `RecommendationResult`; do not raise. See `backend/app/services/ai.py:478-480`:

  ```python
  except Exception as e:
      logger.error(f"Error getting recommendations from AI: {e}", exc_info=True)
      return RecommendationResult(albums=[], raw_response="")
  ```

- Lint config: `backend/ruff.toml` — `line-length = 100`, `target-version = "py311"`.

**Code that must change (verbatim excerpts, current as of `d9c8a91`)**

`backend/app/services/ai.py:95-110` — client init (sync):

```python
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
```

`backend/app/services/ai.py:448-480` — sync calls inside async function:

```python
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
        ...
```

`backend/app/services/ai.py:176-200` — `verify_model_exists` (also sync inside async):

```python
async def verify_model_exists(self) -> dict[str, Any]:
    ...
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
        ...
```

**SDK facts you can rely on:**

- `anthropic>=0.20` ships `anthropic.AsyncAnthropic` with identical `messages.create(...)` signature — just `await` it.
- `google-generativeai>=0.8` ships `GenerativeModel.generate_content_async(...)` with the same args as `generate_content(...)`. Pinned version `0.8.3` already supports it.

## Commands you will need

| Purpose          | Command                                                  | Expected on success            |
|------------------|----------------------------------------------------------|--------------------------------|
| Setup            | `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` | exits 0, no errors |
| Lint             | `cd backend && ruff check app/`                          | exit 0                         |
| Tests            | `cd backend && pytest tests/ -v`                         | all pass                       |
| Smoke (manual)   | `cd backend && uvicorn app.main:app --port 8000` then `curl -s -w "\n%{http_code} %{time_total}s\n" -X POST http://localhost:8000/api/v1/search -H "Content-Type: application/json" -d '{"query":"city pop"}'` | 200 within < 15 s, returns JSON with `recommendations` |

## Scope

**In scope** (the only files you should modify):

- `backend/app/services/ai.py`
- `backend/tests/test_ai_models.py` (extend, do not rewrite)

**Out of scope** (do NOT touch, even though they look related):

- `backend/app/main.py` — the call sites already `await` `ai_service.get_album_recommendations(...)` and `ai_service.verify_model_exists()`. They keep working.
- `backend/app/services/evaluator.py` — pure local computation, no AI calls.
- `backend/requirements.txt` — already has the needed versions; do not bump.
- The retry loop / verification logic / response shape — separate plans handle those.

## Git workflow

- Branch: `advisor/001-async-ai-sdk-clients`
- Commit per logical step (init change, get_album_recommendations change, verify_model_exists change, tests). Message style matches the repo's recent commits (short imperative, occasional emoji prefix in `git log --oneline`); use plain conventional-style: e.g. `perf(ai): use AsyncAnthropic and generate_content_async`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Swap the Claude client to AsyncAnthropic in `_init_clients`

In `backend/app/services/ai.py` change the Claude branch of `_init_clients` (lines ~105-110) from:

```python
claude_key = os.getenv("CLAUDE_API_KEY")
if claude_key:
    self.claude_client = anthropic.Anthropic(api_key=claude_key)
    self.claude_configured = True
else:
    self.claude_configured = False
```

to:

```python
claude_key = os.getenv("CLAUDE_API_KEY")
if claude_key:
    self.claude_client = anthropic.AsyncAnthropic(api_key=claude_key)
    self.claude_configured = True
else:
    self.claude_configured = False
```

Do NOT change the `genai.configure(...)` line — the Gemini SDK is configured globally, and the **model object** is what gets the async method, not the configure call.

**Verify**: `cd backend && python -c "from app.services.ai import AIService; import anthropic; svc = AIService(); print(type(svc.claude_client).__name__ if svc.claude_configured else 'no claude key')"`
→ Expected output: `AsyncAnthropic` (if `CLAUDE_API_KEY` is set in the env) or `no claude key` (if not). If you see `Anthropic`, the change didn't apply.

### Step 2: `await` the Claude call in `get_album_recommendations`

In `backend/app/services/ai.py` change the Claude branch inside `get_album_recommendations` (lines ~458-469) from:

```python
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
```

to:

```python
message = await self.client.messages.create(
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
```

The only addition is the `await` keyword. The method signature and return shape are identical between `Anthropic` and `AsyncAnthropic`.

Note: `self.client` here refers to a property defined elsewhere in `AIService` that returns either the Gemini model or the Claude client based on `self.is_gemini`. You do **not** need to change that property — `AsyncAnthropic` is API-compatible.

**Verify**: `cd backend && ruff check app/services/ai.py` → exit 0. Then `cd backend && python -c "import asyncio; from app.services.ai import AIService; svc = AIService(); print(asyncio.iscoroutinefunction(svc.client.messages.create) if not svc.is_gemini and svc.claude_configured else 'gemini or no key')"`
→ Expected: `True` for the Claude case, otherwise `gemini or no key`.

### Step 3: Use `generate_content_async` for Gemini in `get_album_recommendations`

In `backend/app/services/ai.py` change the Gemini branch inside `get_album_recommendations` (line ~456) from:

```python
if self.is_gemini:
    response = self.client.generate_content(prompt)
    response_text = response.text
```

to:

```python
if self.is_gemini:
    response = await self.client.generate_content_async(prompt)
    response_text = response.text
```

**Verify**: `cd backend && ruff check app/services/ai.py` → exit 0.

### Step 4: Apply the same two changes to `verify_model_exists`

In `backend/app/services/ai.py` change `verify_model_exists` (lines ~176-200) so both branches `await`:

```python
async def verify_model_exists(self) -> dict[str, Any]:
    ...
    try:
        if self.is_gemini:
            response = await self.client.generate_content_async("test")
            result["valid"] = response.text is not None
        else:
            message = await self.client.messages.create(
                model=self.ACTIVE_MODEL,
                max_tokens=5,
                messages=[{"role": "user", "content": "test"}]
            )
            result["valid"] = message.content is not None
    except Exception as e:
        ...
```

**Verify**: `cd backend && ruff check app/services/ai.py` → exit 0.

### Step 5: Add a regression test

In `backend/tests/test_ai_models.py`, add a test that asserts the Claude client is the async type when a Claude model is active. Model after the structure of existing tests in that file (they import `AIService` and assert on its attributes).

Test to add:

```python
import os
import pytest
import anthropic
from app.services.ai import AIService


def test_claude_client_is_async_when_configured(monkeypatch):
    """Regression for plan 001: Claude client must be AsyncAnthropic so the
    event loop is not blocked by AI calls."""
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key-not-used-for-network")
    monkeypatch.setenv("ACTIVE_MODEL", "claude-haiku-4-5-20251001")
    svc = AIService()
    if svc.claude_configured:
        assert isinstance(svc.claude_client, anthropic.AsyncAnthropic), (
            "Claude client must be AsyncAnthropic; sync Anthropic blocks the event loop"
        )
```

**Verify**: `cd backend && pytest tests/test_ai_models.py -v` → all pass, including the new test.

### Step 6: Smoke-test the live search endpoint

Start the server and hit `/api/v1/search` end-to-end to confirm no runtime errors.

```bash
cd backend
uvicorn app.main:app --port 8000 &
SERVER_PID=$!
sleep 3
curl -s -w "\n%{http_code} %{time_total}s\n" -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"city pop"}'
kill $SERVER_PID
```

**Verify**: response is `200`, body parses as JSON with a `recommendations` array. If `500`, read the server logs — most likely a missing `await` somewhere; re-read Steps 2-4.

## Test plan

- New test in `backend/tests/test_ai_models.py`: `test_claude_client_is_async_when_configured` (described in Step 5). Covers the regression that an executor in the future reverts the SDK to `Anthropic`.
- Existing tests in `backend/tests/test_ai_models.py` and `backend/tests/conftest.py` continue to pass unchanged.
- No new test file is created.

Verification: `cd backend && pytest tests/ -v` → all pass.

## Done criteria

ALL must hold:

- [ ] `cd backend && ruff check app/` exits 0.
- [ ] `cd backend && pytest tests/ -v` exits 0 and includes `test_claude_client_is_async_when_configured PASSED`.
- [ ] `grep -nE "anthropic\.Anthropic\(" backend/app/services/ai.py` returns no matches (only `AsyncAnthropic` should remain).
- [ ] `grep -nE "self\.client\.generate_content\(" backend/app/services/ai.py` returns no matches (only `generate_content_async` should remain).
- [ ] `grep -nE "self\.client\.messages\.create\(" backend/app/services/ai.py` shows every match preceded by `await` on the same line.
- [ ] Smoke test in Step 6 returns HTTP 200 with a JSON `recommendations` array.
- [ ] `git status` shows changes only in `backend/app/services/ai.py` and `backend/tests/test_ai_models.py`.
- [ ] `plans/README.md` status row for plan 001 updated to `DONE`.

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts (the codebase has drifted since this plan was written; the SHA `d9c8a91` is the reference).
- `pytest tests/` fails on a test you did not add and the failure references AI/Anthropic/Gemini.
- The smoke test returns 500 and the log says anything like `'coroutine' object has no attribute 'text'` or `'coroutine' object has no attribute 'content'` after Steps 1-4 are complete — that's a missed `await` somewhere; re-read Steps 2-4, but if you can't find it in 10 minutes, stop and report.
- You discover the assumption "`anthropic.AsyncAnthropic` exists in version 0.40.0 with the same `messages.create` signature" is false. Verify with `python -c "import anthropic; print(anthropic.__version__); print(hasattr(anthropic, 'AsyncAnthropic'))"`.
- You discover `generate_content_async` is missing in the installed `google-generativeai` version. Verify with `python -c "import google.generativeai as g; m = g.GenerativeModel('gemini-2.5-flash'); print(hasattr(m, 'generate_content_async'))"`.

## Maintenance notes

For the human/agent who owns this code after the change lands:

- Future SDK upgrades: the v1.x rewrite of `google-generativeai` renames the package to `google-genai` and changes the async API; if `requirements.txt` bumps the major version, re-verify the Gemini async call.
- If a new AI provider is added (e.g. OpenAI), enforce in code review that its client is async and calls are `await`ed — the project pattern is now uniform.
- Reviewer should scrutinize: any new `self.client.<method>(...)` call without `await` inside an `async def`.
- Deferred follow-up: the `set_active_model` function calls `update_render_env_var` (line 494) which still hits Render. After the migration away from Render is complete, that call should be dropped or replaced — out of scope here.
