# Plan 003: Share a connection-pooled httpx.AsyncClient across all external API calls

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md` — unless a reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**: `git diff --stat d9c8a91..HEAD -- backend/app/main.py backend/app/services/render_api.py`
> If any in-scope file changed since this plan was written, compare the "Current state" excerpts against the live code before proceeding; on a mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: perf
- **Planned at**: commit `d9c8a91`, 2026-06-18

## Why this matters

`verify_album_exists` opens a fresh `httpx.AsyncClient` per HTTP call to Spotify (line 599) and per call to Discogs (line 634). A single search verifies 10 albums in parallel → up to 20 brand-new clients per search. Each one pays full TLS handshake + DNS resolution cost, ~50–150 ms each. The same per-call pattern is in `/api/v1/discogs/search` (line 918) and `app/services/render_api.py` (line 39). A module-level client with a connection pool and HTTP keep-alive cuts that overhead to near zero on repeated calls to the same host.

## Current state

**Repository layout (relevant subset)**

- `backend/app/main.py` — FastAPI app. Per-call `httpx.AsyncClient` instances at lines 599, 634, 918, and inside helper functions that fetch Spotify/Discogs data (search by `grep -nE "httpx\.AsyncClient" backend/app/main.py` for the full list).
- `backend/app/services/render_api.py` — `update_render_env_var` uses the same per-call pattern (line 39).

**Conventions** (match these):

- Module-level singletons exist in the codebase: see `backend/app/services/ai.py:509-510` (`ai_service = AIService()`) and `backend/app/services/search_sessions.py:193` (`search_session_service = SearchSessionService()`). Follow that pattern for the shared client.
- FastAPI app lifecycle: the app is created at `backend/app/main.py` near the top via `app = FastAPI(...)`. Lifecycle hooks should use the modern `lifespan` context manager rather than `@app.on_event("startup")`/`("shutdown")` (deprecated in FastAPI 0.93+; this repo uses `fastapi[standard]==0.113.0`).

**Code that must change (verbatim excerpts, current as of `d9c8a91`)**

`backend/app/main.py:597-606` — Spotify verify (per-call client):

```python
if spotify_access_token:
    try:
        async with httpx.AsyncClient() as client:
            search_query = f"album:{title} artist:{artist}"
            search_url = "https://api.spotify.com/v1/search"
            headers = {"Authorization": f"Bearer {spotify_access_token}"}
            params = {"q": search_query, "type": "album", "limit": 5}

            response = await client.get(search_url, headers=headers, params=params, timeout=5.0)
```

`backend/app/main.py:632-647` — Discogs verify (per-call client):

```python
if discogs_key and discogs_secret:
    try:
        async with httpx.AsyncClient() as client:
            search_query = f"{artist} {title}"
            url = "https://api.discogs.com/database/search"
            params = {
                "q": search_query,
                "type": "release",
                "per_page": 10,
                "key": discogs_key,
                "secret": discogs_secret
            }
            headers = {"User-Agent": "DeepCuts/1.0 (contact@deepcuts.com)"}

            response = await client.get(url, params=params, headers=headers, timeout=5.0)
```

`backend/app/main.py:917-933` — `/api/v1/discogs/search` (per-call client; same pattern):

```python
try:
    async with httpx.AsyncClient() as client:
        url = "https://api.discogs.com/database/search"
        params = {...}
        headers = {"User-Agent": "DeepCuts/1.0 (contact@deepcuts.com)"}

        logger.info(f"Calling Discogs API: {url} with query='{request.query}'")
        response = await client.get(url, params=params, headers=headers, timeout=5.0)
```

`backend/app/services/render_api.py:37-42` (similar pattern; in scope so it can move to the shared client).

`backend/requirements.txt` line 7 — `httpx==0.27.0` (already present, no version change needed).

## Commands you will need

| Purpose        | Command                                                            | Expected on success                                                                   |
|----------------|--------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| Setup          | `cd backend && source .venv/bin/activate`                          | venv activated                                                                        |
| Lint           | `cd backend && ruff check app/`                                    | exit 0                                                                                |
| Tests          | `cd backend && pytest tests/ -v`                                   | all pass                                                                              |
| Smoke (manual) | `uvicorn app.main:app --port 8000` then curl `/api/v1/search` ×2  | second search is noticeably faster on the verification phase                          |
| Connection sanity | `python -c "import httpx; c = httpx.AsyncClient(timeout=10.0); print(type(c).__name__)"` | `AsyncClient`                                                            |

## Scope

**In scope** (the only files you should modify):

- `backend/app/main.py`
- `backend/app/services/render_api.py`
- `backend/tests/test_http_client.py` (create)

**Out of scope** (do NOT touch, even though they look related):

- `backend/app/services/ai.py` — uses the Anthropic / Gemini SDKs, not raw httpx. Their connection pooling is the SDK's responsibility.
- `backend/app/services/favorites.py` — no httpx usage.
- `backend/app/services/search_sessions.py` — uses the Supabase Python client, not httpx.
- Spotify token-acquisition function (search for `get_spotify_token` in `main.py`) — it caches the token internally; if it uses httpx, it may use the shared client, but do NOT touch its caching logic.

## Git workflow

- Branch: `advisor/003-shared-pooled-httpx-client`
- Commit per logical step (lifespan + module-level client; refactor per call site; tests). Message style: `perf(http): reuse pooled httpx.AsyncClient across external calls`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Create the shared client and wire it into the FastAPI lifespan

In `backend/app/main.py`:

1. Add `from contextlib import asynccontextmanager` to imports (with other stdlib imports near the top).
2. Just below the imports and before `app = FastAPI(...)`, add the shared client and a lifespan that opens/closes it:

   ```python
   # Shared HTTP client for all external API calls.
   # Reused across Spotify, Discogs, and Render calls so each request benefits
   # from connection pooling + keep-alive (no per-call TLS handshake).
   http_client: httpx.AsyncClient | None = None

   @asynccontextmanager
   async def lifespan(app: FastAPI):
       global http_client
       limits = httpx.Limits(max_connections=100, max_keepalive_connections=20)
       timeout = httpx.Timeout(5.0, connect=3.0)
       http_client = httpx.AsyncClient(limits=limits, timeout=timeout)
       try:
           yield
       finally:
           await http_client.aclose()
           http_client = None
   ```

3. Update the `FastAPI(...)` call to pass `lifespan=lifespan`. If `FastAPI(...)` already takes other kwargs, just add `lifespan=lifespan` to them.

4. Add a small helper at module scope (near where `http_client` is defined) that returns the live client, so call sites have one obvious accessor and a clear error if the lifespan didn't run:

   ```python
   def get_http_client() -> httpx.AsyncClient:
       if http_client is None:
           raise RuntimeError("http_client not initialized; FastAPI lifespan did not run")
       return http_client
   ```

**Verify**:
- `cd backend && ruff check app/main.py` → exit 0.
- `cd backend && python -c "from app.main import lifespan, get_http_client; print('lifespan' if lifespan else 'missing')"` → prints `lifespan`.

### Step 2: Replace the per-call `async with httpx.AsyncClient()` in `verify_album_exists`

In `backend/app/main.py`, in `verify_album_exists` (line ~585), replace both `async with` blocks with calls on the shared client.

For Spotify (current line ~599):

```python
# OLD
async with httpx.AsyncClient() as client:
    search_query = f"album:{title} artist:{artist}"
    ...
    response = await client.get(search_url, headers=headers, params=params, timeout=5.0)

# NEW
search_query = f"album:{title} artist:{artist}"
search_url = "https://api.spotify.com/v1/search"
headers = {"Authorization": f"Bearer {spotify_access_token}"}
params = {"q": search_query, "type": "album", "limit": 5}

response = await get_http_client().get(search_url, headers=headers, params=params, timeout=5.0)
```

For Discogs (current line ~634): same shape — remove the `async with`, call `get_http_client().get(...)` directly. Keep the `try/except` blocks exactly as they are. Keep the `timeout=5.0` keyword (it overrides the default per call, which is the documented httpx pattern).

**Verify**:
- `grep -nE "async with httpx\.AsyncClient" backend/app/main.py` → no matches inside `verify_album_exists` (you may still have matches in `search_discogs` and other helpers; those come in Step 3).
- `cd backend && ruff check app/main.py` → exit 0.

### Step 3: Replace per-call clients in the rest of `main.py` and in `services/render_api.py`

Do the same replacement at every remaining `async with httpx.AsyncClient()` in:

- `backend/app/main.py` — including but not limited to `search_discogs` at line ~917 and any Spotify/Discogs helpers (search with `grep -nE "async with httpx\.AsyncClient" backend/app/main.py`).
- `backend/app/services/render_api.py` line ~39. In this file, since `get_http_client` lives in `main.py`, either:
  - (a) move the helper to a new tiny module `backend/app/http_client.py` and import it from both `main.py` and `render_api.py`, or
  - (b) inline the same `get_http_client()` accessor in `render_api.py` reading from `app.main.http_client`.
  Prefer (a) — fewer cross-module surprises. The new module is ~10 lines:

  ```python
  # backend/app/http_client.py
  import httpx

  http_client: httpx.AsyncClient | None = None

  def set_http_client(client: httpx.AsyncClient | None) -> None:
      global http_client
      http_client = client

  def get_http_client() -> httpx.AsyncClient:
      if http_client is None:
          raise RuntimeError("http_client not initialized; FastAPI lifespan did not run")
      return http_client
  ```

  Then the `lifespan` in `main.py` calls `set_http_client(httpx.AsyncClient(...))` on enter and `set_http_client(None)` on exit. Remove the duplicate `http_client` global from `main.py`.

**Verify**:
- `grep -rnE "async with httpx\.AsyncClient" backend/app/` → no matches anywhere.
- `cd backend && ruff check app/` → exit 0.

### Step 4: Add a regression test that the shared client is reused

Create `backend/tests/test_http_client.py`. Model after `backend/tests/conftest.py` and the existing test file structure.

```python
import httpx
from app import http_client as hc_module


def test_get_http_client_raises_when_not_initialized(monkeypatch):
    """Regression for plan 003: get_http_client must fail loudly if the
    FastAPI lifespan did not set the shared client (mis-imported in a script
    that doesn't run the app)."""
    monkeypatch.setattr(hc_module, "http_client", None)
    try:
        hc_module.get_http_client()
        raised = False
    except RuntimeError:
        raised = True
    assert raised, "get_http_client() must raise RuntimeError when client is None"


def test_shared_client_is_singleton_after_set(monkeypatch):
    fake = httpx.AsyncClient()
    try:
        hc_module.set_http_client(fake)
        assert hc_module.get_http_client() is fake
    finally:
        hc_module.set_http_client(None)
        import asyncio
        asyncio.get_event_loop().run_until_complete(fake.aclose())
```

**Verify**: `cd backend && pytest tests/test_http_client.py -v` → both tests pass.

### Step 5: Smoke-test that searches still work and the second one is faster

Run two consecutive searches and time them. The second should land in less wall time on the verification phase because the pool is warm.

```bash
cd backend
uvicorn app.main:app --port 8000 &
SERVER_PID=$!
sleep 3

echo "=== first search ==="
time curl -s -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"jazz fusion"}' -o /dev/null

echo "=== second search (different query, same hosts; pool should be warm) ==="
time curl -s -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"city pop"}' -o /dev/null

kill $SERVER_PID
```

**Verify**: both return 200; the second `real=` line is lower than the first by a noticeable margin (typically several hundred milliseconds; not a strict gate — variance is high in dev — but should be in that direction).

## Test plan

- New file `backend/tests/test_http_client.py` (Step 4) with two tests.
- Existing tests untouched. `cd backend && pytest tests/ -v` exits 0.
- The shared-client refactor has no end-to-end behavioral test — it relies on the smoke test (Step 5) and the existing search-endpoint smoke test (plan 001 Step 6) continuing to return 200.

## Done criteria

ALL must hold:

- [ ] `grep -rnE "async with httpx\.AsyncClient" backend/app/` returns no matches.
- [ ] `grep -nE "httpx\.AsyncClient\(" backend/app/` returns exactly one construction site (inside `lifespan` in `main.py`, or the helper module).
- [ ] `cd backend && ruff check app/` exits 0.
- [ ] `cd backend && pytest tests/ -v` exits 0; new tests in `test_http_client.py` pass.
- [ ] Smoke test (Step 5) returns 200 for both calls.
- [ ] `git status` shows changes only in in-scope files (plus `backend/app/http_client.py` if you took option (a) in Step 3).
- [ ] `plans/README.md` status row for plan 003 updated to `DONE`.

## STOP conditions

Stop and report back if:

- A call site you find has a wildly different shape (e.g. uses `httpx.Client` synchronously inside a sync helper, or sets unusual transport options) — surface it, don't silently change the behavior.
- The lifespan does not run during tests (FastAPI's `TestClient` runs it; if you use the lower-level `app(...)` calls in any test, it does not) and a test you wrote starts failing on `RuntimeError: http_client not initialized`. The test must initialize the client itself (see the `test_shared_client_is_singleton_after_set` pattern).
- The Spotify or Discogs API starts returning 429s during the smoke test where it didn't before — connection reuse should not cause that, but if it does (unlikely; investigate), stop and report.
- You discover a per-call client somewhere outside `backend/app/` (e.g. in `backend/scripts/` migration scripts) that is in scope of your edits — it isn't. Scripts run once and exit; ignore them.

## Maintenance notes

For the human/agent who owns this code after the change lands:

- The pool defaults (`max_connections=100`, `max_keepalive_connections=20`) are reasonable for a single-instance backend. If the service scales horizontally with high QPS to Spotify/Discogs, those limits can be tuned via env-driven config — out of scope here.
- Reviewer should scrutinize: any new external HTTP call added later that uses `httpx.AsyncClient(...)` directly instead of `get_http_client()`.
- If a future plan adds streaming responses or Server-Sent Events to external APIs (Anthropic streaming?), the shared client still works — but `event_hooks` or per-call `timeout=...` should be passed explicitly.
- Per-call `timeout=5.0` overrides the default — keep it on the verification calls so a slow Spotify response can't stall the user's search beyond the 45 s deadline already in `search_albums`.
