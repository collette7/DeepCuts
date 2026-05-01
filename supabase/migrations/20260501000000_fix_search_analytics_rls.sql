-- =============================================
-- Security Fix: Enable RLS on search analytics tables
-- Addresses: RLS Disabled, Sensitive Columns Exposed
-- Ignores: app_settings (moved to Railway config)
-- =============================================

BEGIN;

-- =============================================
-- search_sessions
-- =============================================
ALTER TABLE search_sessions ENABLE ROW LEVEL SECURITY;

-- Deduplicate: drop all existing policies on this table
DO $$
DECLARE
    pol RECORD;
BEGIN
    FOR pol IN
        SELECT policyname FROM pg_policies
        WHERE tablename = 'search_sessions' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON search_sessions', pol.policyname);
    END LOOP;
END $$;

-- Users can read their own sessions
CREATE POLICY "Users can view own search sessions"
ON search_sessions FOR SELECT
USING (user_email = auth.jwt() ->> 'email');

-- Authenticated users can insert their own sessions
CREATE POLICY "Users can insert own search sessions"
ON search_sessions FOR INSERT
WITH CHECK (auth.role() = 'authenticated' AND user_email = auth.jwt() ->> 'email');

-- Service role bypass (backend uses service key)
CREATE POLICY "Service role can manage search sessions"
ON search_sessions FOR ALL
USING (auth.role() = 'service_role');

-- =============================================
-- search_session_albums
-- =============================================
ALTER TABLE search_session_albums ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    pol RECORD;
BEGIN
    FOR pol IN
        SELECT policyname FROM pg_policies
        WHERE tablename = 'search_session_albums' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON search_session_albums', pol.policyname);
    END LOOP;
END $$;

-- Album ranking data is public (no PII in this table)
CREATE POLICY "Anyone can view search session albums"
ON search_session_albums FOR SELECT
USING (true);

-- Service role bypass
CREATE POLICY "Service role can manage session albums"
ON search_session_albums FOR ALL
USING (auth.role() = 'service_role');

-- =============================================
-- search_session_clicks
-- =============================================
ALTER TABLE search_session_clicks ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    pol RECORD;
BEGIN
    FOR pol IN
        SELECT policyname FROM pg_policies
        WHERE tablename = 'search_session_clicks' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON search_session_clicks', pol.policyname);
    END LOOP;
END $$;

-- Users can read their own click/favorite events
CREATE POLICY "Users can view own session clicks"
ON search_session_clicks FOR SELECT
USING (user_email = auth.jwt() ->> 'email');

-- Authenticated users can insert their own click events
CREATE POLICY "Users can insert own session clicks"
ON search_session_clicks FOR INSERT
WITH CHECK (auth.role() = 'authenticated' AND user_email = auth.jwt() ->> 'email');

-- Service role bypass
CREATE POLICY "Service role can manage session clicks"
ON search_session_clicks FOR ALL
USING (auth.role() = 'service_role');

-- =============================================
-- search_session_filtered_albums
-- Fixes: Multiple Permissive Policies, Auth RLS Init Plan
-- =============================================
ALTER TABLE search_session_filtered_albums ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    pol RECORD;
BEGIN
    FOR pol IN
        SELECT policyname FROM pg_policies
        WHERE tablename = 'search_session_filtered_albums' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON search_session_filtered_albums', pol.policyname);
    END LOOP;
END $$;

-- Users can read their own filtered albums via session ownership
CREATE POLICY "Users can view own filtered albums"
ON search_session_filtered_albums FOR SELECT
USING (
    session_id IN (
        SELECT id FROM search_sessions
        WHERE user_email = auth.jwt() ->> 'email'
    )
);

-- Service role bypass
CREATE POLICY "Service role can manage filtered albums"
ON search_session_filtered_albums FOR ALL
USING (auth.role() = 'service_role');

COMMIT;
