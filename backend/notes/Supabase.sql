
-- My table setup on Supabase


-- Enable UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- USERS
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    preferences JSONB DEFAULT '{}',
    spotify_user_id TEXT,
    spotify_access_token TEXT
);

-- ALBUMS
CREATE TABLE albums (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    spotify_id TEXT UNIQUE,
    discogs_id TEXT,
    genre TEXT,
    mood TEXT,
    release_year INT,
    album_art TEXT,
    spotify_preview_url TEXT,
    spotify_url TEXT,
    cover_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- FAVORITES
CREATE TABLE favorites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    album_id UUID NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    reasoning TEXT,
    saved_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, album_id)
);

-- PLAYLISTS
CREATE TABLE playlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    spotify_playlist_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- PLAYLIST_ALBUMS
CREATE TABLE playlist_albums (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    playlist_id UUID NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    album_id UUID NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    order_index INT,
    UNIQUE(playlist_id, album_id)
);

-- RECOMMENDATION_SESSIONS
CREATE TABLE recommendation_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    source_album_id UUID NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    enhancer_settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RECOMMENDATIONS
CREATE TABLE recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES recommendation_sessions(id) ON DELETE CASCADE,
    recommended_album_id UUID NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    similarity_score FLOAT,
    reason TEXT,
    rank_order INT
);



## RLS

-- USERS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access their own record"
  ON users FOR ALL
  USING (auth.uid() = id);

-- FAVORITES
ALTER TABLE favorites ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access their favorite albums"
  ON favorites FOR ALL
  USING (auth.uid() = user_id);

-- PLAYLISTS
ALTER TABLE playlists ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their playlists"
  ON playlists FOR ALL
  USING (auth.uid() = user_id);

-- PLAYLIST_ALBUMS
ALTER TABLE playlist_albums ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access playlist albums by ownership"
  ON playlist_albums FOR ALL
  USING (
    auth.uid() = (
      SELECT user_id FROM playlists WHERE playlists.id = playlist_albums.playlist_id
    )
  );

-- RECOMMENDATION_SESSIONS
ALTER TABLE recommendation_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can access their own recommendation sessions"
  ON recommendation_sessions FOR ALL
  USING (auth.uid() = user_id);

-- RECOMMENDATIONS
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can read recommendations through their sessions"
  ON recommendations FOR SELECT
  USING (
    auth.uid() = (
      SELECT user_id FROM recommendation_sessions
      WHERE recommendation_sessions.id = recommendations.session_id
    )
  );

-- ALBUMS
ALTER TABLE albums ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access to albums"
  ON albums FOR SELECT
  USING (true);
