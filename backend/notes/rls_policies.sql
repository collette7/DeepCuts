--  RLS policies for email-based authentication

-- USERS table RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can access their own record" ON users;

-- Users can access their own record by email
CREATE POLICY "Users can access their own record by email"
  ON users FOR ALL
  USING (
    auth.jwt() ->> 'email' = email
  );

-- FAVORITES table RLS  
ALTER TABLE favorites ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can access their favorite albums" ON favorites;

-- Users can access their favorites through email lookup
CREATE POLICY "Users can access their favorite albums by email"
  ON favorites FOR ALL
  USING (
    user_id = (
      SELECT id FROM users 
      WHERE email = auth.jwt() ->> 'email'
    )
  );

-- ALBUMS table RLS (keep public read access)
ALTER TABLE albums ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists  
DROP POLICY IF EXISTS "Public read access to albums" ON albums;

-- Public read access to albums
CREATE POLICY "Public read access to albums"
  ON albums FOR SELECT
  USING (true);

-- Allow authenticated users to insert albums (for favorites functionality)
CREATE POLICY "Authenticated users can insert albums"
  ON albums FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');

-- PLAYLISTS table RLS
ALTER TABLE playlists ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can manage their playlists" ON playlists;

-- Users can manage their playlists by email
CREATE POLICY "Users can manage their playlists by email"
  ON playlists FOR ALL
  USING (
    user_id = (
      SELECT id FROM users 
      WHERE email = auth.jwt() ->> 'email'
    )
  );

-- PLAYLIST_ALBUMS table RLS
ALTER TABLE playlist_albums ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can access playlist albums by ownership" ON playlist_albums;

-- Users can access playlist albums by email-based ownership
CREATE POLICY "Users can access playlist albums by email ownership"
  ON playlist_albums FOR ALL
  USING (
    playlist_id IN (
      SELECT p.id FROM playlists p
      INNER JOIN users u ON u.id = p.user_id
      WHERE u.email = auth.jwt() ->> 'email'
    )
  );

-- RECOMMENDATION_SESSIONS table RLS
ALTER TABLE recommendation_sessions ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can access their own recommendation sessions" ON recommendation_sessions;

-- Users can access their recommendation sessions by email
CREATE POLICY "Users can access their recommendation sessions by email"
  ON recommendation_sessions FOR ALL
  USING (
    user_id = (
      SELECT id FROM users 
      WHERE email = auth.jwt() ->> 'email'
    )
  );

-- RECOMMENDATIONS table RLS
ALTER TABLE recommendations ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists
DROP POLICY IF EXISTS "Users can read recommendations through their sessions" ON recommendations;

-- Users can read recommendations through their sessions by email
CREATE POLICY "Users can read recommendations through sessions by email"
  ON recommendations FOR SELECT
  USING (
    session_id IN (
      SELECT rs.id FROM recommendation_sessions rs
      INNER JOIN users u ON u.id = rs.user_id
      WHERE u.email = auth.jwt() ->> 'email'
    )
  );