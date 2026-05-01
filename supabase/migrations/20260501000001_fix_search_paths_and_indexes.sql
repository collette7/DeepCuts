-- =============================================
-- Security Fix: Mutable search paths + index hygiene
-- Addresses: Function Search Path Mutable, Unindexed FKs, Unused Indexes
-- =============================================

BEGIN;

-- =============================================
-- 1. Fix mutable search paths on functions
-- Prevents privilege escalation via search_path manipulation
-- =============================================

-- Fix update_app_settings_timestamp (defined in repo migration)
DO $$
BEGIN
    PERFORM 1 FROM pg_proc WHERE proname = 'update_app_settings_timestamp';
    IF FOUND THEN
        EXECUTE 'ALTER FUNCTION update_app_settings_timestamp() SET search_path = pg_temp, pg_catalog';
    END IF;
END $$;

-- Fix update_updated_at_column (likely auto-created or from older migration)
DO $$
BEGIN
    PERFORM 1 FROM pg_proc WHERE proname = 'update_updated_at_column';
    IF FOUND THEN
        EXECUTE 'ALTER FUNCTION update_updated_at_column() SET search_path = pg_temp, pg_catalog';
    END IF;
END $$;

-- Fix generate_shareable_link (likely from older migration)
DO $$
BEGIN
    PERFORM 1 FROM pg_proc WHERE proname = 'generate_shareable_link';
    IF FOUND THEN
        EXECUTE 'ALTER FUNCTION generate_shareable_link() SET search_path = pg_temp, pg_catalog';
    END IF;
END $$;

-- =============================================
-- 2. Add missing indexes on foreign keys
-- Addresses: Unindexed foreign keys on public.favorites
-- =============================================

CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_album_id ON favorites(album_id);

-- =============================================
-- 3. Drop unused indexes flagged by audit
-- WARNING: Only run if you confirm these indexes are truly unused
-- Uncomment the drops below after verifying via pg_stat_user_indexes
-- =============================================

-- DROP INDEX IF EXISTS idx_app_settings_key;               -- Unused per audit
-- DROP INDEX IF EXISTS idx_recommendation_sessions_user_email; -- Unused per audit
-- DROP INDEX IF EXISTS idx_recommendation_sessions_created_at; -- Unused per audit
-- DROP INDEX IF EXISTS idx_search_sessions_user_email;     -- Unused per audit
-- DROP INDEX IF EXISTS idx_search_sessions_created_at;     -- Unused per audit
-- DROP INDEX IF EXISTS idx_search_session_albums_session;  -- Unused per audit
-- DROP INDEX IF EXISTS idx_search_session_clicks_session;  -- Unused per audit
-- DROP INDEX IF EXISTS idx_search_session_clicks_album;    -- Unused per audit
-- DROP INDEX IF EXISTS idx_filtered_albums_session;        -- Unused per audit

COMMIT;
