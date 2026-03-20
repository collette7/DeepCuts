-- =============================================
-- Search Analytics: track searches, results, clicks, favorites
-- =============================================

BEGIN;

-- Core search sessions table
CREATE TABLE IF NOT EXISTS search_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT NOT NULL,
    user_email TEXT,
    ip_address TEXT,
    user_agent TEXT,
    ai_model TEXT,
    results_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_sessions_user_email ON search_sessions(user_email);
CREATE INDEX IF NOT EXISTS idx_search_sessions_created_at ON search_sessions(created_at DESC);

-- Albums returned per search session
CREATE TABLE IF NOT EXISTS search_session_albums (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES search_sessions(id) ON DELETE CASCADE,
    album_title TEXT NOT NULL,
    album_artist TEXT NOT NULL,
    album_year INT,
    album_genre TEXT,
    rank INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, album_title, album_artist, rank)
);

CREATE INDEX IF NOT EXISTS idx_search_session_albums_session ON search_session_albums(session_id);

-- Track clicks (opening album details) and favorites from search results
CREATE TABLE IF NOT EXISTS search_session_clicks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES search_sessions(id) ON DELETE CASCADE,
    album_title TEXT NOT NULL,
    album_artist TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('click', 'favorite', 'unfavorite')),
    user_email TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_session_clicks_session ON search_session_clicks(session_id);
CREATE INDEX IF NOT EXISTS idx_search_session_clicks_album ON search_session_clicks(album_title, album_artist);

-- Add session_id to favorites table for tracking which search led to a favorite
ALTER TABLE favorites ADD COLUMN IF NOT EXISTS search_session_id UUID REFERENCES search_sessions(id) ON DELETE SET NULL;

COMMIT;
