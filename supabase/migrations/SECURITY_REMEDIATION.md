# Supabase Security Remediation Guide

## Dashboard-Only Settings (Cannot be fixed via migration)

### 1. Auth OTP Long Expiry
**Risk:** Long-lived OTP codes increase window for brute-force/interception attacks.
**Fix:**
1. Go to Supabase Dashboard → Authentication → Email Templates
2. Or: Supabase Dashboard → Authentication → SMTP Settings
3. Set **OTP expiry** to `3600` seconds (1 hour) or less
4. Default recommendation: `600` seconds (10 minutes)

### 2. Leaked Password Protection Disabled
**Risk:** Users with compromised passwords from data breaches can still sign in.
**Fix:**
1. Go to Supabase Dashboard → Authentication → Security
2. Enable **Leaked Password Protection** (also called "HIBP integration" or "Password leak detection")
3. This checks passwords against Have I Been Pwned database on sign-up/reset

### 3. Postgres Version Security Patches
**Risk:** Unpatched PostgreSQL may have known CVEs.
**Fix:**
1. Go to Supabase Dashboard → Database → Infrastructure
2. Check current Postgres version
3. If an upgrade is available, schedule maintenance window
4. Supabase typically handles minor patches automatically; major versions require manual action

---

## Migrations Applied

| Migration | Fixes |
|---|---|
| `20260501000000_fix_search_analytics_rls.sql` | RLS on search_sessions, search_session_albums, search_session_clicks, search_session_filtered_albums |
| `20260501000001_fix_search_paths_and_indexes.sql` | Mutable search paths on 3 functions, unindexed FKs on favorites |

## Remaining Items

| Issue | Status | Action |
|---|---|---|
| Auth OTP Long Expiry | Pending | Dashboard → Auth → SMTP |
| Leaked Password Protection | Pending | Dashboard → Auth → Security |
| Postgres Version Patches | Pending | Dashboard → Database |
| Unused Indexes | Pending | Uncomment DROP statements in migration after verifying via `pg_stat_user_indexes` |
