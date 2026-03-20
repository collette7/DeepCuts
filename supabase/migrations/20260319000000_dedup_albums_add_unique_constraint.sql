-- =============================================
-- Deduplicate albums table and add unique constraint
-- =============================================
-- The albums table has no unique constraint on (title, artist),
-- so repeated AI searches + favorites created duplicate rows.
-- This migration merges duplicates, reassigns foreign keys, and
-- adds a unique index to prevent future dupes.

BEGIN;

-- 1. Build a mapping: for each duplicate set, pick the canonical row
--    (prefer the row with the most metadata, then oldest)
CREATE TEMP TABLE _album_dedup AS
WITH ranked AS (
  SELECT
    id,
    lower(trim(title))  AS norm_title,
    lower(trim(artist)) AS norm_artist,
    ROW_NUMBER() OVER (
      PARTITION BY lower(trim(title)), lower(trim(artist))
      ORDER BY
        (CASE WHEN cover_url   IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN spotify_url IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN genre       IS NOT NULL THEN 1 ELSE 0 END +
         CASE WHEN release_year IS NOT NULL THEN 1 ELSE 0 END) DESC,
        created_at ASC
    ) AS rn
  FROM albums
)
SELECT
  r.id AS dupe_id,
  first_value(r.id) OVER (
    PARTITION BY r.norm_title, r.norm_artist
    ORDER BY r.rn
  ) AS canonical_id
FROM ranked r
WHERE r.rn > 1;

-- 2. Delete favorites that would violate the unique(user_id, album_id)
--    constraint after reassignment (user already has a favorite for the canonical album)
DELETE FROM favorites
WHERE id IN (
  SELECT f_dupe.id
  FROM favorites f_dupe
  JOIN _album_dedup d ON f_dupe.album_id = d.dupe_id
  JOIN favorites f_canon ON f_canon.user_id = f_dupe.user_id
                        AND f_canon.album_id = d.canonical_id
);

-- 3. Reassign remaining favorites from dupes → canonical
UPDATE favorites
SET album_id = d.canonical_id
FROM _album_dedup d
WHERE favorites.album_id = d.dupe_id;

-- 4. Delete the duplicate album rows (CASCADE will clean up any
--    remaining references in recommendation_sessions, playlist_albums, etc.)
DELETE FROM albums
WHERE id IN (SELECT dupe_id FROM _album_dedup);

DROP TABLE _album_dedup;

-- 5. Add unique index on normalized title+artist to prevent future dupes
CREATE UNIQUE INDEX IF NOT EXISTS idx_albums_title_artist_unique
ON albums (lower(trim(title)), lower(trim(artist)));

COMMIT;
