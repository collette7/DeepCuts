-- Drop unused tables from old analytics and playlist features

BEGIN;

DROP TABLE IF EXISTS public.playlist_albums;
DROP TABLE IF EXISTS public.playlists;
DROP TABLE IF EXISTS public.recommendations;
DROP TABLE IF EXISTS public.recommendation_sessions;

COMMIT;
