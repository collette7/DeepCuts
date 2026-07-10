# Plan 004: Run the auth lookup concurrently with the AI call instead of serially before it

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md` — unless a reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**: `git diff --stat d9c8a91..HEAD -- backend/app/main.py`
> If the file changed since this plan was written, compare the "Current state" excerpts against the live code before proceeding; on a mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none (composes with plan 001, 002, 003)
- **Category**: perf
- **Planned at**: commit `d9c8a91`, 2026-06-18

## Why this matters

The first thing the search handler does for authenticated users is a synchronous Supabase Auth call to translate the Bearer token into an email (`supabase_admin.auth.get_user(token)`, `main.py:701`). That round trip costs ~100–300 ms and **blocks every later step** including the AI call. But the email is only consumed at the very end, when writing the search session for analytics. Move the auth lookup off the critical path: kick it off concurrently with the AI call so its cost overlaps with the much larger AI cost rather than adding to it.

## Current state

**Repository layout (relevant subset)**

- `backend/app/main.py` — handler at line 687; current auth block at lines 697-705; first AI call at line 738; result is used at line 844 (`user_email=user_email`).

**Code that must change (verbatim excerpt, current as of `d9c8a91`)**

`backend/app/main.py:694-708`:

```python
"""Get album recommendations based on user query."""
start_time = time.time()

# Get user email if authenticated
user_email = None
if authorization and authorization.startswith("Bearer "):
    try:
        token = authorization.replace("Bearer ", "")
        user_response = supabase_admin.auth.get_user(token)
        if user_response.user:
            user_email = user_response.user.email
    except Exception as e:
        logger.info(f"Search: Could not authenticate user: {e}")

ip_address = http_request.client.host if http_request.client else None
user_agent = http_request.headers.get("user-agent")
```

**Conventions to honor:**

- `asyncio.to_thread(...)` is the idiomatic way to run a sync function in a thread pool without blocking the event loop. Available on Python 3.9+; this repo targets 3.11 (`ruff.toml`).
- `asyncio.create_task(...)` schedules a coroutine without awaiting it, so the AI call can start immediately.
- Errors in auth are swallowed (the code already does this) — keep that behavior; auth is best-effort for analytics.

## Commands you will need

| Purpose        | Command                                                            | Expected on success                                   |
|----------------|--------------------------------------------------------------------|-------------------------------------------------------|
| Setup          | `cd backend && source .venv/bin/activate`                          | venv activated                                        |
| Lint           | `cd backend && ruff check app/`                                    | exit 0                                                |
| Tests          | `cd backend && pytest tests/ -v`                                   | all pass                                              |
| Smoke          | `uvicorn app.main:app --port 8000` + curl with Bearer header below | 200, response time strictly less than before          |

Curl with a real auth token (use any logged-in user's token; the value is only sent to the local server):

```bash
TOKEN="<paste real Supabase access token here>"
curl -s -w "\nHTTP %{http_code} time=%{time_total}s\n" -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"city pop"}' | python3 -m json.tool
```

## Scope

**In scope** (the only files you should modify):

- `backend/app/main.py`
- `backend/tests/test_search_auth_concurrent.py` (create)

**Out of scope**:

- Any change to **what** the email is used for (it still flows into the analytics insert).
- Any change to how the Supabase admin client is constructed.
- The retry loop / verification phase / response shape — separate plans.
- Removing the auth call entirely. (A future plan may, if analytics doesn't need the email; not this plan.)

## Git workflow

- Branch: `advisor/004-run-auth-concurrently-with-ai`
- One or two commits is fine. Message style: `perf(search): run auth lookup concurrently with AI call`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Wrap the auth lookup in a small async helper

Near the top of `backend/app/main.py` (next to other module-level helpers, NOT inside the handler), add an async helper that calls `supabase_admin.auth.get_user` in a thread. This lets the handler `await`-or-`gather` it without modifying the underlying Supabase client.

```python
async def _resolve_user_email_from_token(authorization: str | None) -> str | None:
    """Best-effort: return the authenticated user's email, or None.

    Runs in a worker thread so the sync Supabase auth call does not block
    the event loop. Never raises; failures return None and are logged."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.replace("Bearer ", "", 1)

    def _lookup() -> str | None:
        try:
            user_response = supabase_admin.auth.get_user(token)
            if user_response and user_response.user:
                return user_response.user.email
        except Exception as e:
            logger.info(f"Search: Could not authenticate user: {e}")
        return None

    return await asyncio.to_thread(_lookup)
```

Add `import asyncio` to the imports at the top of the file if it isn't already present (it likely is — verify with `grep -n "^import asyncio" backend/app/main.py`).

**Verify**:
- `cd backend && ruff check app/main.py` → exit 0.
- `grep -n "_resolve_user_email_from_token" backend/app/main.py` → at least 1 match (the definition).

### Step 2: Kick the auth lookup off as a concurrent task at the top of the handler

In `backend/app/main.py` `search_albums` (line ~688), replace the existing sync auth block (lines 697-705) with a `create_task`:

```python
"""Get album recommendations based on user query."""
start_time = time.time()

# Kick off auth resolution concurrently — its result is only needed at the
# very end (analytics). Don't pay the round-trip serially before the AI call.
user_email_task = asyncio.create_task(_resolve_user_email_from_token(authorization))

ip_address = http_request.client.host if http_request.client else None
user_agent = http_request.headers.get("user-agent")
```

### Step 3: Await the task only when its result is needed

Find the spot where `user_email` is consumed. In the current code that is the call to `search_session_service.create_session(...)` at line ~841 (or, after plan 002 lands, the `background_tasks.add_task(...)` call to `record_search`).

Just before that consumption, await the task:

```python
user_email = await user_email_task
```

That's it. By the time the AI call (1–10 s) + verification phase have completed, `user_email_task` will almost certainly already be done — the `await` just collects its result without adding latency.

**Verify**:
- `grep -nE "supabase_admin\.auth\.get_user" backend/app/main.py` → no matches inside `search_albums`. The only match should be inside `_resolve_user_email_from_token`.
- `grep -nE "user_email = await user_email_task" backend/app/main.py` → exactly one match.
- `cd backend && ruff check app/main.py` → exit 0.

### Step 4: Add a regression test

Create `backend/tests/test_search_auth_concurrent.py`. Use `monkeypatch` to assert the auth helper is invoked exactly once with the token and returns the expected email without raising on bad input. Model after `backend/tests/test_ai_models.py`.

```python
import asyncio
import pytest
from app import main as main_module


@pytest.mark.asyncio
async def test_resolve_user_email_returns_none_for_missing_authorization():
    assert await main_module._resolve_user_email_from_token(None) is None
    assert await main_module._resolve_user_email_from_token("") is None
    assert await main_module._resolve_user_email_from_token("Basic abc") is None


@pytest.mark.asyncio
async def test_resolve_user_email_swallows_supabase_errors(monkeypatch):
    class _BoomClient:
        class auth:
            @staticmethod
            def get_user(token):
                raise RuntimeError("simulated outage")

    monkeypatch.setattr(main_module, "supabase_admin", _BoomClient)
    # Must NOT raise; returns None on failure.
    assert await main_module._resolve_user_email_from_token("Bearer x") is None


@pytest.mark.asyncio
async def test_resolve_user_email_returns_email_on_success(monkeypatch):
    class _OkClient:
        class auth:
            @staticmethod
            def get_user(token):
                class _Resp:
                    class user:
                        email = "person@example.com"
                return _Resp()

    monkeypatch.setattr(main_module, "supabase_admin", _OkClient)
    assert await main_module._resolve_user_email_from_token("Bearer x") == "person@example.com"
```

`pytest.ini` already has `asyncio_mode = auto`, so the `@pytest.mark.asyncio` annotations are optional. They're included here for explicitness.

**Verify**: `cd backend && pytest tests/test_search_auth_concurrent.py -v` → all three tests pass.

### Step 5: Smoke-test that authenticated searches still attribute correctly

Run an authenticated search against the local server, then query Supabase Studio (or psql) to confirm the row has the email.

```bash
cd backend
uvicorn app.main:app --port 8000 &
SERVER_PID=$!
sleep 3

TOKEN="<paste real Supabase access token>"
curl -s -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"smoke 004"}' > /tmp/resp_004.json
SID=$(python3 -c "import json; print(json.load(open('/tmp/resp_004.json'))['session_id'])")
echo "Session: $SID"
sleep 3
# In Supabase Studio SQL editor, run:
#   select id, user_email, query from search_input where id = '<paste $SID>';
# Expected: user_email matches the token's owner.

kill $SERVER_PID
```

**Verify**: the row exists and `user_email` matches the token owner. If `user_email` is NULL when it should not be, the await in Step 3 may be in the wrong place — verify it runs before the analytics call.

## Test plan

- New file `backend/tests/test_search_auth_concurrent.py` with three tests (Step 4).
- Existing tests untouched; `cd backend && pytest tests/ -v` exits 0.
- The end-to-end attribution check is the smoke test in Step 5.

## Done criteria

ALL must hold:

- [ ] `grep -nE "supabase_admin\.auth\.get_user" backend/app/main.py` shows no matches inside the body of `search_albums` (only inside the helper).
- [ ] `grep -nE "asyncio\.create_task\(_resolve_user_email_from_token" backend/app/main.py` returns exactly one match in `search_albums`.
- [ ] `grep -nE "user_email = await user_email_task" backend/app/main.py` returns exactly one match.
- [ ] `cd backend && ruff check app/` exits 0.
- [ ] `cd backend && pytest tests/ -v` exits 0; new tests pass.
- [ ] Smoke (Step 5) attributes the search to the correct `user_email`.
- [ ] `git status` shows changes only in in-scope files.
- [ ] `plans/README.md` status row for plan 004 updated to `DONE`.

## STOP conditions

Stop and report back if:

- The handler has been refactored since `d9c8a91` and the sync auth block no longer matches the excerpt — re-read the live code before changing anything.
- `supabase_admin` is not a module-level name in `backend/app/main.py`. Confirm with `grep -n "^supabase_admin\|^[[:space:]]*supabase_admin = " backend/app/main.py`. If it lives elsewhere, surface it before guessing.
- The smoke test's `user_email` is consistently NULL on the resulting row — the await is in the wrong place, OR the Supabase JWT secret/the admin client is misconfigured. Don't paper over it.
- You discover the auth result is used in *more* places than the analytics insert (e.g. a rate-limit check, an ownership filter) — that means it's actually on the critical path and this plan's assumption is wrong; stop and report.

## Maintenance notes

For the human/agent who owns this code after the change lands:

- If a future feature needs `user_email` earlier (e.g. per-user rate limiting before the AI call), the await moves up. That's expected and fine — the concurrency optimization is opportunistic.
- Reviewer should scrutinize: any new code path that consumes `user_email` *before* the `await user_email_task` line. Either move the consumer down or move the `await` up.
- Deferred follow-up: if analytics ends up not needing the email (e.g. anonymized in the future), this whole code path can be deleted. Track that conversation outside this plan.
