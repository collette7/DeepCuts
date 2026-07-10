# Plan 002: Defer search-session DB writes to FastAPI BackgroundTasks so the response returns immediately

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md` — unless a reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**: `git diff --stat d9c8a91..HEAD -- backend/app/main.py backend/app/services/search_sessions.py`
> If any in-scope file changed since this plan was written, compare the "Current state" excerpts against the live code before proceeding; on a mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: perf
- **Planned at**: commit `d9c8a91`, 2026-06-18

## Why this matters

After the AI call and album verification finish, the search endpoint runs two-to-three synchronous Supabase inserts (search session, output albums, filtered albums) before sending the response. Those inserts cross the public internet to Supabase Kong and serialize over the GIL, adding ~100–300 ms of tail latency the user sees nothing happening during. The data is pure analytics — the response never needs to wait for it. Moving the writes to FastAPI's `BackgroundTasks` returns the response as soon as recommendations are ready and runs the writes after the connection closes.

## Current state

**Repository layout (relevant subset)**

- `backend/app/main.py` — FastAPI app. Search handler at line 687; current synchronous analytics writes at lines 841 and 853.
- `backend/app/services/search_sessions.py` — `SearchSessionService` class. Wraps Supabase inserts. Currently `create_session(...)` returns the Postgres-generated UUID (line 49), which the response includes as `session_id`.
- `backend/app/models/albums.py` — `SearchResponse` Pydantic model. `session_id: str | None`.

**Conventions** (match these):

- Logging via `logger = logging.getLogger('deepcuts')`. Do NOT use `print` (the existing `search_sessions.py` does — copy the pattern from `main.py` instead, see `backend/app/main.py:705`: `logger.info(f"...")`).
- Errors in analytics paths are logged and swallowed; they must not fail the response. Example from `backend/app/services/search_sessions.py:69-71`:

  ```python
  except Exception as e:
      print(f"Error creating search session: {e}")
      return None
  ```

  (The existing code uses `print`. Keep the swallow-and-continue behavior but switch to `logger.error(..., exc_info=True)` per the rest of the codebase.)

- FastAPI dependency style: handlers take `http_request: Request` and other params via type hints — see `backend/app/main.py:688-692`.

**Code that must change (verbatim excerpts, current as of `d9c8a91`)**

`backend/app/main.py:687-692` — handler signature:

```python
@app.post("/api/v1/search")
async def search_albums(
    request: SearchRequest,
    http_request: Request,
    authorization: str = Header(None)
) -> SearchResponse:
```

`backend/app/main.py:841-857` — current inline analytics writes after recommendations are built:

```python
session_id = search_session_service.create_session(
    query=request.query,
    albums=recommendations,
    user_email=user_email,
    ai_model=ai_service.ACTIVE_MODEL,
    raw_results_count=raw_count,
    filtered_count=len(filtered_albums),
    ip_address=ip_address,
    user_agent=user_agent,
    raw_response=raw_response,
)

if session_id and filtered_albums:
    search_session_service.track_filtered_albums(session_id, filtered_albums)

# Limit results for response
limited_recommendations = recommendations[:request.max_results]
```

`backend/app/services/search_sessions.py:20-67` — `create_session` (relevant portion):

```python
def create_session(
    self,
    query: str,
    albums: list[AlbumData],
    user_email: str | None = None,
    ai_model: str | None = None,
    raw_results_count: int = 0,
    filtered_count: int = 0,
    ip_address: str | None = None,
    user_agent: str | None = None,
    raw_response: str | None = None,
) -> str | None:
    if not albums:
        return None
    try:
        session_data = {
            "query": query,
            ...
        }
        result = self.supabase.table("search_input").insert(session_data).execute()
        if not result.data:
            return None
        session_id = result.data[0]["id"]

        if albums:
            album_rows = [...]
            if album_rows:
                self.supabase.table("search_output").insert(album_rows).execute()

        return session_id
```

**Schema fact** (verified from the migrated database via earlier psql checks): the `search_input.id` column is a UUID primary key with default `uuid_generate_v4()`. Inserting a row with an explicit `id` value overrides the default — this is standard Postgres behavior. That enables generating the UUID in Python *before* the insert so the response can include it without waiting for the DB roundtrip.

## Commands you will need

| Purpose        | Command                                          | Expected on success                                                                                                          |
|----------------|--------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| Setup          | `cd backend && source .venv/bin/activate`        | activates venv                                                                                                               |
| Lint           | `cd backend && ruff check app/`                  | exit 0                                                                                                                       |
| Tests          | `cd backend && pytest tests/ -v`                 | all pass                                                                                                                     |
| Smoke (manual) | `uvicorn app.main:app --port 8000` + curl below  | response includes a non-null `session_id` and returns in well under the previous time; logs show "wrote search session" after |
| Curl           | `curl -s -X POST http://localhost:8000/api/v1/search -H "Content-Type: application/json" -d '{"query":"city pop"}' \| python3 -m json.tool` | JSON with `session_id` (UUID string), `recommendations` array. |

## Scope

**In scope** (the only files you should modify):

- `backend/app/main.py`
- `backend/app/services/search_sessions.py`
- `backend/tests/test_search_sessions.py` (create)

**Out of scope** (do NOT touch, even though they look related):

- `backend/app/services/favorites.py` — separate analytics path, different lifecycle (the favorite endpoint already returns synchronously and the user expects confirmation; do not defer it).
- The Supabase schema — do not write a migration. The `id` column already has a UUID default; this plan exploits that, it does not change it.
- The retry/eval loop in `backend/app/main.py:730-810` — a separate plan handles it.
- The Authorization header / auth lookup in `backend/app/main.py:697-705` — a separate plan handles it.

## Git workflow

- Branch: `advisor/002-defer-db-writes-to-background-tasks`
- Commit per step (split signature change, call-site refactor, tests). Message style: `perf(search): defer session writes to BackgroundTasks`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Extend `create_session` to accept a pre-generated `session_id`

In `backend/app/services/search_sessions.py`, modify `create_session` so the caller can pass a UUID. Default to `None` for backwards compatibility (other call paths, if any, keep working). When passed, include it in the insert payload and return it. When not passed, behavior is unchanged.

New signature:

```python
def create_session(
    self,
    query: str,
    albums: list[AlbumData],
    user_email: str | None = None,
    ai_model: str | None = None,
    raw_results_count: int = 0,
    filtered_count: int = 0,
    ip_address: str | None = None,
    user_agent: str | None = None,
    raw_response: str | None = None,
    session_id: str | None = None,   # NEW
) -> str | None:
```

In the function body, when `session_id` is provided, add `"id": session_id` to `session_data` before the insert. Either way, read the returned id from `result.data[0]["id"]` as the function does today.

Also: replace the `print(...)` in the `except` block (line 70) with `logger.error("Error creating search session: %s", e, exc_info=True)`. Add `import logging` and `logger = logging.getLogger('deepcuts')` at the module top if not already present.

**Verify**: `cd backend && ruff check app/services/search_sessions.py` → exit 0.

### Step 2: Extract analytics work into a single helper that does **all** writes

Still in `backend/app/services/search_sessions.py`, add a new public method on `SearchSessionService` that performs `create_session` + `track_filtered_albums` in one call. The handler will queue this single helper as the background task.

```python
def record_search(
    self,
    *,
    session_id: str,
    query: str,
    albums: list[AlbumData],
    filtered_albums: list[dict[str, str]],
    user_email: str | None,
    ai_model: str | None,
    raw_results_count: int,
    filtered_count: int,
    ip_address: str | None,
    user_agent: str | None,
    raw_response: str | None,
) -> None:
    """Best-effort: write the search session and filtered-album rows.
    Called from a FastAPI BackgroundTask after the response is sent; must
    never raise (analytics never fails a request)."""
    try:
        sid = self.create_session(
            query=query,
            albums=albums,
            user_email=user_email,
            ai_model=ai_model,
            raw_results_count=raw_results_count,
            filtered_count=filtered_count,
            ip_address=ip_address,
            user_agent=user_agent,
            raw_response=raw_response,
            session_id=session_id,
        )
        if sid and filtered_albums:
            self.track_filtered_albums(sid, filtered_albums)
    except Exception as e:
        logger.error("record_search failed: %s", e, exc_info=True)
```

**Verify**: `cd backend && ruff check app/services/search_sessions.py` → exit 0.

### Step 3: Generate the UUID in the handler and queue the background task

In `backend/app/main.py`:

1. Add `BackgroundTasks` and `uuid` to the imports at the top of the file. (`from fastapi import ..., BackgroundTasks` — keep alphabetical with existing FastAPI imports if a convention is visible; `import uuid` with the other stdlib imports.)
2. Add a `background_tasks: BackgroundTasks` parameter to the handler signature:

   ```python
   @app.post("/api/v1/search")
   async def search_albums(
       request: SearchRequest,
       http_request: Request,
       background_tasks: BackgroundTasks,
       authorization: str = Header(None)
   ) -> SearchResponse:
   ```

3. Replace the inline write block (lines 841-854) with a UUID generation + a `background_tasks.add_task(...)` call:

   ```python
   session_id = str(uuid.uuid4())
   background_tasks.add_task(
       search_session_service.record_search,
       session_id=session_id,
       query=request.query,
       albums=list(recommendations),
       filtered_albums=list(filtered_albums),
       user_email=user_email,
       ai_model=ai_service.ACTIVE_MODEL,
       raw_results_count=raw_count,
       filtered_count=len(filtered_albums),
       ip_address=ip_address,
       user_agent=user_agent,
       raw_response=raw_response,
   )
   ```

   The `list(...)` copies guarantee the background task sees the data even if the handler later mutates them (it currently slices `recommendations` for the response).

4. Leave `limited_recommendations = recommendations[:request.max_results]` and the rest of the response construction unchanged. The `session_id` returned in `SearchResponse` is now the locally-generated UUID — semantically the same identifier the DB will store.

**Verify**: `cd backend && ruff check app/main.py` → exit 0. Then `grep -nE "search_session_service\.(create_session|track_filtered_albums)" backend/app/main.py` → only the line you just added that calls `record_search` should remain (no direct calls to `create_session` or `track_filtered_albums` from `main.py`).

### Step 4: Add a unit test for `record_search`

Create `backend/tests/test_search_sessions.py` and add a test that exercises `record_search` end-to-end with a mocked Supabase client. Model after `backend/tests/test_ai_models.py` (same imports of `monkeypatch`, same lightweight style).

```python
from unittest.mock import MagicMock
import pytest
from app.services.search_sessions import SearchSessionService
from app.models.albums import AlbumData


@pytest.fixture
def svc(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://localhost")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test")
    s = SearchSessionService.__new__(SearchSessionService)
    s.url = "http://localhost"
    s.key = "test"
    s.supabase = MagicMock()
    return s


def test_record_search_uses_provided_session_id_and_does_not_raise(svc):
    # supabase.table(...).insert(...).execute() returns an object with .data
    chain = svc.supabase.table.return_value.insert.return_value.execute
    chain.return_value.data = [{"id": "provided-uuid"}]

    svc.record_search(
        session_id="provided-uuid",
        query="city pop",
        albums=[AlbumData(id="a1", title="A", artist="X", year=1980, genre="city pop")],
        filtered_albums=[{"title": "Fake", "artist": "Y", "reason": "not_found"}],
        user_email=None,
        ai_model="claude-haiku-4-5-20251001",
        raw_results_count=10,
        filtered_count=1,
        ip_address=None,
        user_agent=None,
        raw_response="",
    )

    # Insert was called at least once for search_input; the payload included our id.
    insert_calls = svc.supabase.table.return_value.insert.call_args_list
    payloads = [c.args[0] for c in insert_calls]
    assert any(isinstance(p, dict) and p.get("id") == "provided-uuid" for p in payloads), (
        "record_search must pass the provided session_id into the search_input insert"
    )


def test_record_search_swallows_exceptions(svc):
    svc.supabase.table.side_effect = RuntimeError("simulated outage")

    # Must not raise — analytics never fails a request.
    svc.record_search(
        session_id="x",
        query="q",
        albums=[AlbumData(id="a1", title="A", artist="X", year=1980, genre="g")],
        filtered_albums=[],
        user_email=None,
        ai_model=None,
        raw_results_count=0,
        filtered_count=0,
        ip_address=None,
        user_agent=None,
        raw_response="",
    )
```

**Verify**: `cd backend && pytest tests/test_search_sessions.py -v` → both tests pass.

### Step 5: Smoke-test the live endpoint

Start the server and confirm the response includes a UUID `session_id` and arrives faster than before. Then wait a few seconds and check the DB to confirm the row landed.

```bash
cd backend
uvicorn app.main:app --port 8000 &
SERVER_PID=$!
sleep 3
curl -s -w "\nHTTP %{http_code}  time=%{time_total}s\n" -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"smoke test query 002"}' | tee /tmp/resp.json
sleep 5
# Confirm the session_id from the response landed in the DB:
SID=$(python3 -c "import json; print(json.load(open('/tmp/resp.json'))['session_id'])")
echo "Looking up session $SID in Supabase…"
# (This requires psql to the self-hosted Supabase. If not available locally, log into Supabase Studio and run:
#   select id, query from search_input where id = '<SID>';)
kill $SERVER_PID
```

**Verify**: response is `200` with a `session_id` that's a valid UUID, and the same UUID is queryable in the `search_input` table within a few seconds.

## Test plan

- New file `backend/tests/test_search_sessions.py` with two tests (Step 4): one asserts the pre-generated session id is passed through; one asserts exceptions are swallowed.
- Existing tests untouched. `cd backend && pytest tests/ -v` exits 0.

## Done criteria

ALL must hold:

- [ ] `cd backend && ruff check app/` exits 0.
- [ ] `cd backend && pytest tests/ -v` exits 0; both new tests in `test_search_sessions.py` are present and pass.
- [ ] `grep -nE "search_session_service\.create_session\(|search_session_service\.track_filtered_albums\(" backend/app/main.py` returns no matches (all writes now go through `record_search` via `BackgroundTasks`).
- [ ] `grep -n "BackgroundTasks" backend/app/main.py` shows it in both the imports and the `search_albums` signature.
- [ ] Smoke test in Step 5 returns 200, a UUID-shaped `session_id`, and that UUID is present in the `search_input` table within ~5 s.
- [ ] `git status` shows changes only in the in-scope files.
- [ ] `plans/README.md` status row for plan 002 updated to `DONE`.

## STOP conditions

Stop and report back if:

- The code at the locations in "Current state" doesn't match the excerpts (drift since `d9c8a91`).
- The smoke test's `session_id` does not appear in the `search_input` table after waiting 30 s — that means the background task is being dropped, likely because the FastAPI request worker terminated mid-task. Investigate, do not silently change to a synchronous write.
- You discover that `search_input.id` does NOT have a default that allows client-supplied UUIDs (e.g. the insert raises `null value in column "id"` when omitted, or `permission denied` when supplied). Verify via the Supabase Studio SQL editor: `select column_name, column_default from information_schema.columns where table_name = 'search_input' and column_name = 'id';`. Expected: a non-null default like `uuid_generate_v4()` or `gen_random_uuid()`.
- The Pydantic `SearchResponse.session_id` validation rejects the UUID string format. (It is typed `str | None`, so this should not happen — but if it does, stop.)

## Maintenance notes

For the human/agent who owns this code after the change lands:

- If a future plan adds **real-time** features (e.g. streaming recommendations as they're verified), the BackgroundTask pattern still works for the final analytics flush but the response shape may change.
- Reviewer should scrutinize: any future code path that depends on the analytics row existing *before* the response is sent (it no longer does). For example, if the frontend tries to `GET /api/v1/sessions/{id}/analytics` immediately after a search, it may 404 briefly.
- Deferred follow-up: `track_click`, `track_favorite`, and `get_sessions` in `search_sessions.py` still use sync `print`-based error handling. They are out of scope for this plan but the same logger pattern from Step 1 should be applied next time they're touched.
- The `record_search` helper is the single seam to use for any future analytics inserts in the search flow.
