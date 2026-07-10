# Plan 005: Remove the automatic verification-retry loop, return first attempt, and add an `exclude` knob so the frontend can request "more results" without duplicates

> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report — do not improvise. When done, update the status row for this plan in `plans/README.md` — unless a reviewer dispatched you and told you they maintain the index.
>
> **Drift check (run first)**: `git diff --stat d9c8a91..HEAD -- backend/app/main.py backend/app/models/albums.py backend/app/services/ai.py`
> If any in-scope file changed since this plan was written, compare the "Current state" excerpts against the live code before proceeding; on a mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: none (composes best after 001-004 land, but does not require them)
- **Category**: perf
- **Planned at**: commit `d9c8a91`, 2026-06-18

## Why this matters

The search handler currently re-runs the full AI + verification loop up to three times whenever fewer than 10 albums verify (`main.py:730-810`). For most users that doesn't improve perceived quality — 7 good recommendations now is better than 10 recommendations after another 5–10 second wait — but it always charges the user the full retry cost on the wall clock. Worst case is ~3× the necessary latency. This plan deletes the auto-retry, returns the first attempt's results immediately, and exposes counts so the frontend can show a "Find more results" button. That button re-calls `/api/v1/search` with the list of albums already shown in an `exclude` field; the backend includes those in the AI prompt so it returns fresh, non-duplicate picks, and the UI appends them.

## Current state

**Repository layout (relevant subset)**

- `backend/app/main.py` — search handler with retry loop at lines 730-810; `verify_album_exists` at line 585; `RecommendationResult` and `evaluator` consumed inside the loop.
- `backend/app/services/ai.py` — `get_album_recommendations` at line 448; `get_recommendation_prompt` at line 249 builds the user prompt for the AI.
- `backend/app/services/evaluator.py` — pure local evaluator; produces feedback strings fed back into the AI on retry (currently used at `main.py:804-810`).
- `backend/app/models/albums.py` — `SearchRequest` (line 40) and `SearchResponse` (line 64).

**Conventions to honor:**

- Pydantic v2 (the repo pins `pydantic==2.11.7`). Use `Field(default_factory=list)` for list defaults; `default=None` for optional scalars; `BaseModel.model_validate(...)` if validating dicts (not used here).
- Response shapes are documented with `Field(..., description=...)` — see `backend/app/models/albums.py:64-73`. Match that.
- Errors that block the user get raised as `HTTPException(503, detail=...)`; analytics-only errors are logged and swallowed.

**Code that must change (verbatim excerpts, current as of `d9c8a91`)**

`backend/app/models/albums.py:40-73` — request/response shapes:

```python
class SearchRequest(BaseModel):
    """Search requests to claude for album recommendations"""
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Name of album"
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Max number of recommendations to return"
    )
    include_spotify: bool = Field(
        default=True,
        description="Include Spotify preview URLs"
    )
    include_discogs: bool = Field(
        default=True,
        description="Include Discogs marketplace links"
    )
    # ... possibly more fields below; do not delete any

class SearchResponse(BaseModel):
    """Recommendations"""
    query: str = Field(..., description="Original search query")
    recommendations: list[AlbumData] = Field(
        default_factory=list,
        description="List of recommended albums"
    )
    total_found: int = Field(..., description="Total number")
    processing_time_ms: int = Field(..., description="Time taken to process request")
    session_id: str | None = Field(None, description="Search session ID for analytics")
```

`backend/app/main.py:717-812` — the retry loop to delete (preserving only the first iteration's logic):

```python
try:
    max_attempts = 3
    attempt = 0
    best_recommendations: list[AlbumData] = []
    best_filtered: list[dict[str, str]] = []
    best_raw_count = 0
    best_raw_response = ""
    feedback = ""
    ai_error = None

    # Global 45-second timeout for entire search operation
    search_deadline = time.time() + 45

    while attempt < max_attempts:
        attempt += 1
        logger.info(f"AI recommendation attempt {attempt}/{max_attempts}")

        if time.time() > search_deadline:
            logger.warning("Search deadline exceeded, returning best effort results")
            break

        result = await ai_service.get_album_recommendations(request.query, feedback)
        recommendations = result.albums
        raw_response = result.raw_response
        raw_count = len(recommendations)

        if not recommendations or raw_count == 0:
            logger.warning(f"No recommendations from AI for query: {request.query}")
            if attempt < max_attempts:
                feedback = "Your previous response contained no valid recommendations. Please provide 10 real albums."
                continue
            verify = await ai_service.verify_model_exists()
            if not verify["valid"]:
                ai_error = verify.get("error", "AI model returned no response")
            break

        # Verify all albums in parallel (was sequential — 10× slower)
        verification_tasks = [
            verify_album_exists(album.title, album.artist)
            for album in recommendations
        ]
        verification_results = await asyncio.gather(*verification_tasks, return_exceptions=True)

        filtered_albums: list[dict[str, str]] = []
        verified_recommendations: list[AlbumData] = []
        verified_map: dict[str, bool] = {}

        for album, result in zip(recommendations, verification_results):
            album_key = f"{album.title} by {album.artist}"
            is_verified = result if not isinstance(result, Exception) else False
            verified_map[album_key] = is_verified

            if is_verified:
                verified_recommendations.append(album)
            else:
                # ... filtered_albums append ...

        removed_count = raw_count - len(verified_recommendations)
        # ... best_* tracking ...

        if len(verified_recommendations) == 10:
            best_recommendations = verified_recommendations
            best_filtered = filtered_albums
            best_raw_count = raw_count
            best_raw_response = raw_response
            logger.info("Achieved 10 verified albums")
            break

        if attempt < max_attempts:
            if not verified_recommendations:
                feedback = "All albums failed verification. Please provide real, verifiable albums."
            else:
                evaluation = evaluator.evaluate(
                    recommendations,
                    request.query,
                    verified_map=verified_map
                )
                feedback = evaluator.get_feedback_prompt(recommendations, evaluation)
                logger.info(f"Retrying with feedback: {feedback[:200]}...")
        else:
            logger.warning(f"Max attempts reached. Using best effort with {len(best_recommendations)} verified albums.")
```

`backend/app/services/ai.py:249-...` — `get_recommendation_prompt(album_name)` builds the system+user prompt. (Read the full body during Step 2; do not edit it speculatively.)

## Commands you will need

| Purpose        | Command                                                              | Expected on success                                    |
|----------------|----------------------------------------------------------------------|--------------------------------------------------------|
| Setup          | `cd backend && source .venv/bin/activate`                            | venv activated                                         |
| Lint           | `cd backend && ruff check app/`                                      | exit 0                                                 |
| Tests          | `cd backend && pytest tests/ -v`                                     | all pass                                               |
| Smoke first    | `uvicorn app.main:app --port 8000` then curl below                   | 200, lower wall time than before for queries that previously retried, response includes `verified_count`, `attempted_count` |
| Smoke "more"   | curl again with `exclude` populated from the first response          | 200, returned albums have no overlap with the excluded set |

```bash
# First search
curl -s -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query":"obscure shoegaze 1991"}' | tee /tmp/r1.json | python3 -m json.tool

# Build exclude list from the response
EXCLUDE=$(python3 -c "import json; r=json.load(open('/tmp/r1.json')); print(json.dumps([f\"{a['title']}|{a['artist']}\" for a in r['recommendations']]))")
echo "Excluding: $EXCLUDE"

# "Find more" search — same query, exclude what we already have
curl -s -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"obscure shoegaze 1991\", \"exclude\": $EXCLUDE}" | python3 -m json.tool
```

## Scope

**In scope** (the only files you should modify):

- `backend/app/main.py` — handler refactor.
- `backend/app/models/albums.py` — request/response shape additions.
- `backend/app/services/ai.py` — accept `exclude` in `get_album_recommendations` and surface it in the prompt.
- `backend/tests/test_search_endpoint.py` (create) — endpoint tests covering the new shape and the exclude path.

**Out of scope** (do NOT touch, even though they look related):

- `backend/app/services/evaluator.py` — without the retry loop, the feedback path is dead. **Do not delete the file or the class** in this plan; another plan can revisit it once we're sure no other caller wants the evaluator. Just stop calling it from `search_albums`.
- Any frontend code (`frontend/src/...`). The "find more" button and the request-payload construction are a separate frontend plan.
- The `verify_album_exists` function itself — only its caller changes.
- The 45-second `search_deadline` — keep it as a global cap on the first attempt; just remove the retry-loop logic around it.
- Any change to album-attribute fields on `AlbumData` — only the search request/response wrappers change.

## Git workflow

- Branch: `advisor/005-user-driven-retry-and-find-more`
- Commit per logical step: (1) model fields, (2) AI service `exclude` plumbing, (3) handler refactor, (4) tests. Message style: `feat(search): user-driven retry; remove auto-retry loop`.
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: Extend `SearchRequest` and `SearchResponse` with the new fields

In `backend/app/models/albums.py`:

Add to `SearchRequest`:

```python
exclude: list[str] = Field(
    default_factory=list,
    max_length=100,
    description=(
        "Album keys formatted as 'title|artist' to exclude from results. "
        "Used by the 'find more results' flow to avoid returning albums the "
        "user has already seen."
    ),
)
```

Add to `SearchResponse`:

```python
attempted_count: int = Field(
    default=0,
    description="Number of albums the AI returned before verification.",
)
verified_count: int = Field(
    default=0,
    description="Number of albums that passed Spotify/Discogs verification (= len(recommendations)).",
)
filtered: list[dict[str, str]] = Field(
    default_factory=list,
    description=(
        "Albums the AI returned but verification rejected, with 'title', "
        "'artist', and 'reason'. Useful for showing 'we excluded N likely-fake "
        "results' in the UI."
    ),
)
```

**Verify**:
- `cd backend && ruff check app/models/albums.py` → exit 0.
- `cd backend && python -c "from app.models.albums import SearchRequest, SearchResponse; r = SearchRequest(query='x'); print(r.exclude); print(SearchResponse.model_fields.keys())"` → prints `[]` and the set of field names including `attempted_count`, `verified_count`, `filtered`.

### Step 2: Plumb `exclude` into `get_album_recommendations` and the AI prompt

In `backend/app/services/ai.py`:

1. Change the signature of `get_album_recommendations` to accept an optional exclude list:

   ```python
   async def get_album_recommendations(
       self,
       album_name: str,
       feedback: str = "",
       exclude: list[str] | None = None,
   ) -> RecommendationResult:
   ```

   The `feedback` parameter stays (its second caller is `verify_model_exists`-adjacent code paths; harmless to keep as an unused-by-default knob — easier rollback if the retry decision is reverted later).

2. After `prompt = self.get_recommendation_prompt(album_name)`, but before the AI call, append an explicit exclude instruction when the list is non-empty:

   ```python
   if exclude:
       # Normalize to "Title by Artist" lines so the model can read them naturally.
       formatted = []
       for key in exclude:
           if "|" in key:
               t, a = key.split("|", 1)
               formatted.append(f"- {t.strip()} by {a.strip()}")
           else:
               formatted.append(f"- {key.strip()}")
       prompt += (
           "\n\nDo NOT recommend any of these albums (the user has already seen them):\n"
           + "\n".join(formatted)
           + "\n\nReturn entirely new recommendations."
       )
   ```

3. Keep the rest of the function body identical.

**Verify**:
- `cd backend && ruff check app/services/ai.py` → exit 0.
- `cd backend && python -c "import inspect; from app.services.ai import AIService; print(inspect.signature(AIService.get_album_recommendations))"` → signature shows `exclude: list[str] | None = None`.

### Step 3: Replace the retry loop with a single attempt in `search_albums`

In `backend/app/main.py`, in `search_albums` (line ~687), replace the entire `try:` block from `max_attempts = 3` (line ~718) down to the `else: logger.warning(f"Max attempts reached...")` (line ~812) with a single-attempt version. Keep the surrounding code (auth/IP/user-agent block before, response construction after) intact. Specifically:

```python
try:
    # Single attempt — no auto-retry. If the user wants more results they
    # POST again with `exclude` set (plan 005).
    search_deadline = time.time() + 45  # belt-and-braces upper bound

    if time.time() > search_deadline:
        raise HTTPException(status_code=504, detail="Search timed out before starting.")

    result = await ai_service.get_album_recommendations(
        request.query,
        exclude=request.exclude,
    )
    recommendations: list[AlbumData] = result.albums
    raw_response = result.raw_response
    raw_count = len(recommendations)

    if not recommendations:
        verify = await ai_service.verify_model_exists()
        if not verify["valid"]:
            ai_error = verify.get("error", "AI model returned no response")
        else:
            ai_error = "AI returned no recommendations for this query. Try rephrasing."
        raise HTTPException(status_code=503, detail=safe_error_message(ai_error))

    # Filter out anything the caller asked to exclude, just in case the model
    # ignored the instruction. Keys are "Title|Artist".
    excluded_keys = {key.strip().lower() for key in request.exclude}
    if excluded_keys:
        recommendations = [
            a for a in recommendations
            if f"{a.title}|{a.artist}".lower() not in excluded_keys
        ]

    # Verify all albums in parallel.
    verification_tasks = [
        verify_album_exists(album.title, album.artist)
        for album in recommendations
    ]
    verification_results = await asyncio.gather(*verification_tasks, return_exceptions=True)

    filtered_albums: list[dict[str, str]] = []
    verified_recommendations: list[AlbumData] = []

    for album, vr in zip(recommendations, verification_results):
        is_verified = vr if not isinstance(vr, Exception) else False
        if is_verified:
            verified_recommendations.append(album)
        else:
            if isinstance(vr, Exception):
                logger.warning(f"Verification error for {album.title}: {vr}")
            filtered_albums.append({
                "title": album.title,
                "artist": album.artist,
                "reason": "not_found",
            })

    recommendations = verified_recommendations
    raw_count_after_filter = raw_count  # what the AI returned before verification
```

Now replace the response-construction block. Keep the `AlbumData` re-shaping loop (it strips `spotify_preview_url`, etc.) — that part is unchanged. Update the `SearchResponse(...)` construction at the bottom of the handler to include the new fields:

```python
processing_time = int((time.time() - start_time) * 1000)

return SearchResponse(
    query=request.query,
    recommendations=limited_recommendations,
    total_found=len(limited_recommendations),
    processing_time_ms=processing_time,
    session_id=session_id,
    attempted_count=raw_count_after_filter,
    verified_count=len(limited_recommendations),
    filtered=filtered_albums,
)
```

Remove the `from app.services.evaluator import evaluator` import from `main.py` if it's now unused (verify with `grep -nE "evaluator\." backend/app/main.py` — if no matches outside the import, drop the import line). The evaluator class and file stay; just disconnect this caller.

**Verify**:
- `grep -nE "while attempt < max_attempts" backend/app/main.py` → no matches.
- `grep -nE "best_recommendations|best_filtered|best_raw_count|best_raw_response" backend/app/main.py` → no matches.
- `grep -nE "evaluator\.evaluate|evaluator\.get_feedback_prompt" backend/app/main.py` → no matches.
- `cd backend && ruff check app/main.py` → exit 0.

### Step 4: Add endpoint tests covering the new shape and the exclude path

Create `backend/tests/test_search_endpoint.py`. Use FastAPI's `TestClient` and `monkeypatch` the AI + verification functions so tests are hermetic (no real network).

```python
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app
from app.models.albums import AlbumData
from app.services.ai import RecommendationResult


@pytest.fixture
def client(monkeypatch):
    # Fake the AI service so each test controls what it returns.
    fake_albums = [
        AlbumData(id=f"a{i}", title=f"Album {i}", artist=f"Artist {i}", year=1990 + i, genre="rock")
        for i in range(7)
    ]
    monkeypatch.setattr(
        main_module.ai_service,
        "get_album_recommendations",
        AsyncMock(return_value=RecommendationResult(albums=fake_albums, raw_response="raw")),
    )
    monkeypatch.setattr(main_module.ai_service, "is_ready", True, raising=False)
    monkeypatch.setattr(
        main_module,
        "verify_album_exists",
        AsyncMock(return_value=True),
    )
    return TestClient(app)


def test_search_returns_new_count_fields(client):
    resp = client.post("/api/v1/search", json={"query": "city pop"})
    assert resp.status_code == 200
    body = resp.json()
    assert "attempted_count" in body
    assert "verified_count" in body
    assert "filtered" in body
    assert body["verified_count"] == len(body["recommendations"])


def test_search_does_not_retry_when_some_albums_unverified(client, monkeypatch):
    # Verification rejects every other album. The handler must NOT call the AI
    # service again (no auto-retry).
    call_count = {"n": 0}

    async def flaky_verify(title, artist):
        call_count.setdefault("v", 0)
        call_count["v"] += 1
        return call_count["v"] % 2 == 0

    monkeypatch.setattr(main_module, "verify_album_exists", flaky_verify)

    ai_calls = {"n": 0}
    orig = main_module.ai_service.get_album_recommendations

    async def counting_ai(*args, **kwargs):
        ai_calls["n"] += 1
        return await orig(*args, **kwargs)

    monkeypatch.setattr(main_module.ai_service, "get_album_recommendations", counting_ai)

    resp = client.post("/api/v1/search", json={"query": "shoegaze"})
    assert resp.status_code == 200
    assert ai_calls["n"] == 1, (
        "Plan 005 removed the auto-retry; the AI must be called exactly once per request."
    )


def test_search_with_exclude_drops_excluded_albums(client):
    # The AI fixture always returns "Album 0".."Album 6". Exclude "Album 0|Artist 0".
    resp = client.post(
        "/api/v1/search",
        json={"query": "city pop", "exclude": ["Album 0|Artist 0"]},
    )
    assert resp.status_code == 200
    titles = [a["title"] for a in resp.json()["recommendations"]]
    assert "Album 0" not in titles
```

**Verify**: `cd backend && pytest tests/test_search_endpoint.py -v` → all three tests pass.

### Step 5: Smoke-test the live endpoint and the "find more" flow

Use the two curls from "Commands you will need". Expect:
- First call: returns 200, `verified_count` > 0, `attempted_count >= verified_count`, `filtered` is a list.
- Second call (with `exclude`): returns 200, none of the new recommendations share `"title|artist"` keys with the excluded set.

If the second response **does** contain duplicates, log + check whether the AI ignored the prompt (likely — the `exclude` filter in Step 3 is the defensive backstop). The filter should remove them server-side regardless. If duplicates still leak through, recheck the `excluded_keys` set construction.

## Test plan

- New file `backend/tests/test_search_endpoint.py` (Step 4) with three tests covering: new response fields, no auto-retry, exclude filtering.
- Existing tests untouched.
- Verification: `cd backend && pytest tests/ -v` exits 0.

## Done criteria

ALL must hold:

- [ ] `grep -nE "while attempt < max_attempts" backend/app/main.py` returns no matches.
- [ ] `grep -nE "best_recommendations|best_filtered|best_raw_count" backend/app/main.py` returns no matches.
- [ ] `grep -nE "evaluator\." backend/app/main.py` shows at most the (now-removable) import line; ideally zero matches.
- [ ] `cd backend && ruff check app/` exits 0.
- [ ] `cd backend && pytest tests/ -v` exits 0; new tests in `test_search_endpoint.py` pass.
- [ ] First smoke curl (Step 5) returns 200 with `verified_count`, `attempted_count`, `filtered` present.
- [ ] Second smoke curl (Step 5) with `exclude` populated returns 200 and no duplicates with the excluded set.
- [ ] `git status` shows changes only in in-scope files.
- [ ] `plans/README.md` status row for plan 005 updated to `DONE`.

## STOP conditions

Stop and report back if:

- The handler in `main.py` is materially different from the excerpt in "Current state" (e.g. retry loop already removed, or rewritten in a different shape) — drift since `d9c8a91`.
- Removing the evaluator caller breaks an import elsewhere — verify with `grep -rn "from app.services.evaluator" backend/app/`. Plan 005 only removes the call site, not the file.
- The TestClient tests fail with `RuntimeError: http_client not initialized` — plan 003 may have landed; the lifespan needs to run during tests. Solution: use `with TestClient(app) as client:` (context-manager form, which runs the lifespan). If plan 003 has NOT landed, this won't apply.
- You discover the AI consistently ignores the "do not recommend these albums" instruction — that means the prompt addition in Step 2 needs the model to receive it earlier or more emphatically. The Step 3 backstop filter still works correctly; report the prompt-quality issue separately.
- The AI returns vastly fewer results when `exclude` is large (say 30+ items eat into the response space). Document this as a follow-up — the realistic ceiling is 1–2 "find more" rounds anyway.

## Maintenance notes

For the human/agent who owns this code after the change lands:

- The frontend follow-up is a separate plan: it must (a) render `attempted_count - verified_count` as "we filtered N likely-fake results" if non-zero, (b) show a "Find more results" button when `verified_count == max_results` (i.e. AI delivered a full page; the user might want another), (c) POST again with `exclude` built from the union of all currently-rendered albums, and (d) append the new results to the existing list rather than replace.
- The `evaluator` module is now dead code from the search path. Decision needed: delete it (it's only ~212 lines) or keep it as a candidate for future "quality-score" features. Do not silently delete it in another change without a plan.
- Reviewer should scrutinize: any new code that imports `evaluator` or reintroduces a server-side retry; the plan deliberately removes both.
- The `exclude` list is unbounded in the AI prompt but capped at 100 entries in `SearchRequest`. If users start hitting that cap, the right answer is paginated "load more" of a single search result set, not a bigger exclude — track that as a future feature, not a knob bump.
- Long-term: once analytics confirms that most users don't click "find more" (or that they always do, etc.), revisit whether the AI prompt should still aim for exactly 10 recommendations. The system has more headroom now without the auto-retry.
