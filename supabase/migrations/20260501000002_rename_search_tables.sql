-- =============================================
-- Rename search analytics tables + add raw_response
-- search_sessions -> search_input
-- search_session_albums -> search_output
-- =============================================

BEGIN;

-- =============================================
-- 1. Drop policies that reference search_sessions by name
-- =============================================

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

-- =============================================
-- 2. Rename tables
-- =============================================

ALTER TABLE search_sessions RENAME TO search_input;
ALTER TABLE search_session_albums RENAME TO search_output;

-- =============================================
-- 3. Add raw_response column for debugging AI hallucinations
-- =============================================

ALTER TABLE search_input ADD COLUMN IF NOT EXISTS raw_response TEXT;

-- =============================================
-- 4. Recreate RLS policies with updated table names
-- =============================================

-- search_input
ALTER TABLE search_input ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    pol RECORD;
BEGIN
    FOR pol IN
        SELECT policyname FROM pg_policies
        WHERE tablename = 'search_input' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON search_input', pol.policyname);
    END LOOP;
END $$;

CREATE POLICY "Users can view own search input"
ON search_input FOR SELECT
USING (user_email = auth.jwt() ->> 'email');

CREATE POLICY "Users can insert own search input"
ON search_input FOR INSERT
WITH CHECK (auth.role() = 'authenticated' AND user_email = auth.jwt() ->> 'email');

CREATE POLICY "Service role can manage search input"
ON search_input FOR ALL
USING (auth.role() = 'service_role');

-- search_output
ALTER TABLE search_output ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    pol RECORD;
BEGIN
    FOR pol IN
        SELECT policyname FROM pg_policies
        WHERE tablename = 'search_output' AND schemaname = 'public'
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS %I ON search_output', pol.policyname);
    END LOOP;
END $$;

CREATE POLICY "Anyone can view search output"
ON search_output FOR SELECT
USING (true);

CREATE POLICY "Service role can manage search output"
ON search_output FOR ALL
USING (auth.role() = 'service_role');

-- search_session_clicks
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

CREATE POLICY "Users can view own session clicks"
ON search_session_clicks FOR SELECT
USING (user_email = auth.jwt() ->> 'email');

CREATE POLICY "Users can insert own session clicks"
ON search_session_clicks FOR INSERT
WITH CHECK (auth.role() = 'authenticated' AND user_email = auth.jwt() ->> 'email');

CREATE POLICY "Service role can manage session clicks"
ON search_session_clicks FOR ALL
USING (auth.role() = 'service_role');

-- search_session_filtered_albums
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

CREATE POLICY "Users can view own filtered albums"
ON search_session_filtered_albums FOR SELECT
USING (
    session_id IN (
        SELECT id FROM search_input
        WHERE user_email = auth.jwt() ->> 'email'
    )
);

CREATE POLICY "Service role can manage filtered albums"
ON search_session_filtered_albums FOR ALL
USING (auth.role() = 'service_role');

COMMIT;
