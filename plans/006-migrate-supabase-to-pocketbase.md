# Migrate DeepCuts from Supabase to PocketBase

Created: 2026-07-09

## Problem and goal

The Hetzner server has 4 GB RAM and currently runs the full self-hosted Supabase stack alongside Coolify and the DeepCuts FastAPI application. Supabase contributes most of the server's container and memory overhead despite very light usage. The goal is to replace Supabase with one PocketBase service while preserving authentication, favorites, search-history analytics, and the existing FastAPI contract.

Paths in this plan are relative to the DeepCuts repository. The backend is currently deployed at `/app` inside the Coolify application container.

## Current-state audit

- FastAPI remains the public application API at `api.deepcuts.casa`.
- Supabase Auth contains six email/password users; five have confirmed email addresses.
- Application data is currently empty.
- Persistent objects consist of seven tables: `users`, `albums`, `favorites`, `search_input`, `search_output`, `search_session_clicks`, and `search_session_filtered_albums`.
- `search_results` and `search_summary` are SQL views, not tables.
- No Supabase Storage buckets or objects exist.
- No tables are configured for Supabase Realtime publication.
- `hello` is the only user Edge Function and is an unused sample; `main` is Supabase's generic Edge Runtime router.
- The API uses Supabase directly from `backend/app/database.py`, `backend/app/main.py`, `backend/app/services/favorites.py`, `backend/app/services/search_sessions.py`, and `backend/app/services/recommendations.py`.
- `recommendation_sessions` is referenced by code but does not exist in the deployed database; the service appears unused.
- The frontend uses Supabase sessions, password login, signup, email confirmation, and magic-link OTP login.
- The deployed container contains an older copied Dockerfile with Supabase keys embedded as build arguments, although the current checked-in `backend/Dockerfile` is clean. Treat the exposed values as compromised and rotate them.

## Scope

### Included

- Deploy PocketBase through Coolify with persistent storage and backups.
- Recreate the active data model, relationships, uniqueness constraints, and access rules.
- Move the six accounts to PocketBase through a password-reset flow.
- Replace Supabase calls in FastAPI while preserving existing HTTP response shapes.
- Update the frontend authentication client and token storage to PocketBase.
- Replace the existing magic-link flow with email/password login, email verification, and password reset.
- Test, cut over, monitor, retain a rollback path, and then retire Supabase.

### Excluded

- Storage migration, because no objects exist.
- Realtime migration, because no tables use it.
- Porting the sample `hello` Edge Function.
- Reimplementing passwordless magic-link authentication; that can be a separate PocketBase hook project if it is wanted later.
- Directly copying password hashes into PocketBase's internal database.
- Removing FastAPI or moving business logic into PocketBase hooks.

## Key decisions

1. **Keep FastAPI as the application boundary.** PocketBase will provide persistence and authentication; FastAPI will continue to own authorization checks, business logic, enrichment, and public endpoint compatibility.
2. **Use a small typed `httpx` adapter instead of an unofficial Python PocketBase SDK.** This keeps the dependency surface controlled and makes HTTP behavior easy to fake in tests.
3. **Use one PocketBase auth collection named `users`.** Merge the existing public profile fields into the auth records so the separate Supabase `auth.users` and `public.users` split disappears.
4. **Require password resets for all six users.** Create accounts by email, preserve confirmed state where appropriate, and send reset links after SMTP is configured. Do not mutate PocketBase's SQLite internals to import hashes.
5. **Compute `search_results` and `search_summary` in FastAPI.** These are read models rather than independent data, and keeping them in the API avoids coupling the migration to SQLite view behavior.
6. **Do not dual-write.** Because the data tables are empty and traffic is small, use a short maintenance cutover after full staging verification. Dual-write would add more failure modes than protection.
7. **Retire magic-link login for this migration.** All six existing accounts have passwords, so the lowest-risk path is PocketBase password login plus verification/reset emails. Preserve magic links only as a separately scoped custom-auth feature.
8. **Authenticate FastAPI to PocketBase dynamically.** Store superuser credentials in Coolify, obtain short-lived admin tokens at runtime, cache them in memory, and reauthenticate once on an admin 401. Never store an expiring admin token as static configuration.

## Target collections

| PocketBase collection | Source | Important rules and constraints |
|---|---|---|
| `users` (auth) | `auth.users` + `public.users` | Unique email; self-readable and self-editable profile; fields for username, preferences, Spotify ID and tokens |
| `albums` | `public.albums` | Public read; backend-managed writes; unique normalized title/artist and optional unique Spotify ID |
| `favorites` | `public.favorites` | Relations to user and album; unique user/album pair; only the owning user may read or mutate through application flows |
| `search_inputs` | `public.search_input` | Backend writes; authenticated users may read their own records |
| `search_outputs` | `public.search_output` | Relation to search input; public read only if the current product behavior truly requires it, otherwise owner-only |
| `search_clicks` | `public.search_session_clicks` | Relation to search input; validate action as click/favorite/unfavorite |
| `filtered_albums` | `public.search_session_filtered_albums` | Relation to search input; owner-only reads |

## Implementation units

### U1. Secure the existing deployment

**Goal:** Rotate exposed Supabase credentials and remove security/debug leakage before further migration work.

**Files:** `backend/Dockerfile`, `backend/.env.example`, `backend/app/main.py`, Coolify environment configuration.

**Approach:** Confirm the checked-in Dockerfile remains secret-free, inspect the deployed image history, rotate the exposed Supabase keys, and redeploy from the current source. Keep secrets only in Coolify runtime environment variables. Remove or authenticate debug endpoints that reveal API-key prefixes. Record all five Supabase client creation sites so the migration cannot leave a hidden dependency behind: two in `backend/app/database.py` and one each in `backend/app/main.py`, `backend/app/services/favorites.py`, and `backend/app/services/search_sessions.py`.

**Test scenarios:** Build inspection finds no Supabase token value in Docker history; the redeployed API starts using runtime secrets; requests requiring Supabase continue to work before migration.

### U2. Add a persistence and authentication boundary

**Goal:** Stop endpoint and service code from depending directly on Supabase's query builder and auth objects.

**Dependencies:** U1.

**Files:** `backend/app/database.py`, `backend/app/config.py`, new `backend/app/clients/pocketbase.py`, new `backend/app/services/auth.py`, new `backend/tests/test_pocketbase_client.py`, new `backend/tests/test_auth.py`.

**Approach:** Define small operations around actual use cases: verify token, fetch/create user, upsert album, add/remove/list favorite, write search events, and fetch analytics. Implement them through PocketBase REST endpoints with explicit timeouts, typed errors, and dependency injection. Preserve the current backend contract in which authenticated dependencies return the user's email, despite variables sometimes being named `user_id`. Add `POCKETBASE_URL` and server-side superuser credentials without deleting Supabase settings yet. Cache the admin token, reauthenticate on expiry/401, retry once, and surface a controlled failure if reauthentication fails.

**Test scenarios:** Valid token returns the expected user email; invalid/expired user token maps to HTTP 401; expired admin token reauthenticates and retries once; failed admin reauthentication maps to a controlled 503; PocketBase timeout maps to a controlled 503; collection errors do not leak credentials or internal responses; test doubles can run without external services.

### U3. Deploy PocketBase in parallel

**Goal:** Establish a production-shaped PocketBase instance without affecting current traffic.

**Dependencies:** U1.

**Files:** Coolify PocketBase service definition, persistent `pb_data` volume, backup configuration.

**Approach:** Pin a PocketBase release rather than using `latest`; expose it initially on a new hostname such as `data.deepcuts.casa`; attach a persistent volume; restrict the admin dashboard; configure SMTP before user migration; and create scheduled application backups plus an off-server copy.

**Test scenarios:** Restart preserves collections and records; TLS works; the admin dashboard is not publicly open without authentication; backup creation and restore to a disposable instance succeed.

### U4. Define versioned PocketBase schema migrations

**Goal:** Reproduce the active schema and authorization behavior deterministically.

**Dependencies:** U3.

**Files:** new `pocketbase/pb_migrations/*_create_users.js`, `pocketbase/pb_migrations/*_create_albums.js`, `pocketbase/pb_migrations/*_create_favorites.js`, `pocketbase/pb_migrations/*_create_search_collections.js`, new `backend/tests/test_schema_contract.py`.

**Approach:** Create collections through committed JavaScript migrations. Model foreign keys as relation fields and recreate required uniqueness/index constraints. Translate RLS intent into PocketBase API rules, but keep privileged writes server-side through FastAPI. Do not add `recommendation_sessions` unless a route-level usage audit proves it is needed.

**Test scenarios:** A clean PocketBase instance reaches the expected schema from migrations alone; duplicate favorite and album identities are rejected; deleting a search input handles child records as designed; unauthenticated and cross-user collection access is denied.

### U5. Replace Supabase data operations in FastAPI

**Goal:** Preserve API behavior while changing the persistence implementation.

**Dependencies:** U2, U4.

**Files:** `backend/app/main.py`, `backend/app/services/favorites.py`, `backend/app/services/search_sessions.py`, delete `backend/app/services/recommendations.py`, `backend/app/services/ai.py`, `backend/tests/test_search_endpoint.py`, new `backend/tests/test_favorites.py`, new `backend/tests/test_search_sessions.py`, new `backend/tests/test_analytics.py`.

**Approach:** Route all authentication and data access through the new boundary and remove every module-level Supabase client. Replace nested selects with explicit PocketBase relation expansion or small service-layer queries. Reimplement `/api/v1/analytics/search-results` and `/api/v1/analytics/search-summary` in Python instead of querying SQL views. Preserve the current `get_sessions` behavior intentionally by filtering out sessions with no clicks, or approve the behavior change before release; PocketBase expansion does not reproduce Supabase's `!inner` join automatically. Fix the existing `track_favorite` call so the `favorited` boolean and `user_email` arguments are passed correctly. Require authentication and ownership checks for `/api/v1/analytics/sessions/{session_id}`, which currently exposes session details without authentication. Delete the unused recommendations service rather than recreating its nonexistent table.

**Test scenarios:** Search creates the parent record and all expected child records; partial logging failure does not break recommendation delivery; favorite and unfavorite events record the correct action and email; favorites are idempotent per user/album; email-based identity lookup works end-to-end; users cannot read or change another user's favorites/history; unauthenticated or cross-user session-detail access returns 401/403; search-results and search-summary response shapes remain compatible; sessions-without-clicks behavior matches the approved contract; PocketBase outages produce controlled failures.

### U6. Migrate frontend authentication

**Goal:** Replace Supabase sessions with PocketBase sessions while deliberately moving the visible login experience from password-or-magic-link to password-based authentication.

**Dependencies:** U2, U3.

**Files:** replace `frontend/src/lib/supabase.ts` with `frontend/src/lib/pocketbase.ts`, modify `frontend/src/app/contexts/AuthContext.tsx`, `frontend/src/app/components/auth/LoginForm.tsx`, `frontend/src/app/components/auth/SignupForm.tsx`, `frontend/src/app/components/auth/AuthModal.tsx`, `frontend/src/app/auth/callback/page.tsx`, `frontend/src/lib/api.ts`, `frontend/src/lib/auth-error-handler.ts`, frontend environment template, and auth tests.

**Approach:** Replace Supabase login, logout, session restoration, and bearer-token retrieval with the official PocketBase JavaScript SDK. Remove passwordless branches from `signIn` and `signUp`; replace them with password login, verification, forgot-password, and reset-password flows. Redesign `/auth/callback` because PocketBase confirmation/reset redirects do not produce Supabase sessions in the URL. Continue sending the bearer token to FastAPI. Handle expired sessions by refreshing or returning the user to login. Before cutover, retain the last known-good Supabase frontend deployment so the hosting provider can roll back immediately without rebuilding from changed environment variables.

**Test scenarios:** Password signup triggers verification; verified login persists across reload; forgot/reset password completes successfully; the former magic-link UI is absent; confirmation/reset callbacks show success and error states; logout clears PocketBase auth state; expired tokens are handled without loops; authenticated API requests carry the PocketBase token; unauthenticated routes continue to work; rollback deployment still authenticates against Supabase.

### U7. Migrate the six users

**Goal:** Preserve account identity while moving credentials safely.

**Dependencies:** U3, U4, U6.

**Files:** new `scripts/export_supabase_users.py`, new `scripts/import_pocketbase_users.py`, new `backend/tests/test_user_migration.py`.

**Approach:** Export only required identity metadata, excluding password hashes and tokens. Create six PocketBase auth records with normalized email addresses and profile fields. Preserve confirmed status for the five confirmed users; explicitly review the one unconfirmed account. Trigger password-reset emails and verify delivery before cutover.

**Test scenarios:** Running import twice does not duplicate users; all six emails map one-to-one; no password hash or Supabase token appears in export artifacts; confirmed/unconfirmed handling matches the approved mapping; a reset password can successfully authenticate.

### U8. Stage and cut over

**Goal:** Switch production with a clear rollback point.

**Dependencies:** U5, U6, U7.

**Approach:** Take a final Supabase database dump and record current environment configuration. Preserve the last known-good Supabase backend image and frontend deployment as explicit rollback artifacts. Run backend and frontend smoke tests against PocketBase. Announce a short maintenance window, stop writes, repeat the user/data export if necessary, update Coolify environment variables, deploy backend and frontend, and validate production flows before reopening traffic.

**Test scenarios:** Health endpoint reports PocketBase connected; anonymous search works; login/reset works; favorites add/list/update/remove works; search history and analytics work; restart preserves data; memory usage remains stable under representative traffic.

### U9. Observe, roll back if necessary, then decommission Supabase

**Goal:** Remove the heavy stack only after production confidence is established.

**Dependencies:** U8.

**Approach:** Keep Supabase stopped but intact during a seven-day rollback window. Monitor authentication failures, PocketBase latency, FastAPI errors, disk growth, backup success, RAM, and swap. Roll back by restoring the previous environment and restarting Supabase if a release-blocking issue appears. After acceptance, archive the final dump, remove Supabase containers and secrets, and reclaim volumes only after verifying the archive.

**Test scenarios:** Documented rollback restores the previous login and API flows; PocketBase backup restore is proven; Supabase secrets are absent from Coolify and images; server memory remains materially below the previous baseline.

## Cutover acceptance checklist

- All six users exist in PocketBase and receive a usable password-reset path.
- Existing frontend and FastAPI endpoint contracts remain compatible.
- Favorites and search-history authorization is owner-scoped.
- Anonymous search remains available.
- No production code imports or initializes the Supabase client.
- No Supabase credentials remain in Dockerfiles, image history, frontend bundles, or Coolify after decommissioning.
- PocketBase survives restart and has a tested off-server backup.
- Supabase can still be restarted during the rollback window.

## Risks

- **Password reset delivery:** SMTP must be proven before cutover or users will be locked out.
- **Magic-link removal:** This is a user-visible authentication change and should be announced before cutover.
- **Admin-token expiry:** FastAPI must reauthenticate automatically or PocketBase access will eventually fail after an apparently healthy deployment.
- **SQLite write contention:** Current traffic is small, but search-event writes should be load-tested and monitored.
- **API-rule drift:** FastAPI authorization and PocketBase rules must agree; tests should cover both owner and cross-user access.
- **Schema drift in code:** The unused `recommendation_sessions` references and SQL views must be deliberately removed or recreated rather than silently ignored.
- **Single-node durability:** PocketBase is lightweight but remains a single-node SQLite service; off-server backups are mandatory.

## Recommended execution order

U1 first; U2 and U3 can then proceed in parallel; U4 follows U3; U5 follows U2 and U4; U6 can proceed alongside U4–U5; U7 follows schema and frontend auth; U8 performs cutover; U9 owns observation and decommissioning.
