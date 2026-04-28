-- =============================================
-- Search Analytics: add verification tracking
-- =============================================

BEGIN;

-- Track how many albums were filtered out
ALTER TABLE search_sessions ADD COLUMN IF NOT EXISTS filtered_count INT DEFAULT 0;
ALTER TABLE search_sessions ADD COLUMN IF NOT EXISTS raw_results_count INT DEFAULT 0;

-- Track per-album verification status
ALTER TABLE search_session_albums ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT true;
ALTER TABLE search_session_albums ADD COLUMN IF NOT EXISTS verification_source TEXT;

-- New table for albums that were filtered out
CREATE TABLE IF NOT EXISTS search_session_filtered_albums (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES search_sessions(id) ON DELETE CASCADE,
    album_title TEXT NOT NULL,
    album_artist TEXT NOT NULL,
    filter_reason TEXT, -- 'not_found', 'api_error'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_filtered_albums_session ON search_session_filtered_albums(session_id);

-- RLS for filtered albums table
ALTER TABLE search_session_filtered_albums ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own filtered albums"
ON search_session_filtered_albums FOR SELECT
USING (
    session_id IN (
        SELECT id FROM search_sessions
        WHERE user_email = auth.jwt() ->> 'email'
    )
);

CREATE POLICY "Service role can manage filtered albums"
ON search_session_filtered_albums FOR ALL
USING (auth.role() = 'service_role');

COMMIT;