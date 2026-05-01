-- =============================================
-- Fix: Views must respect RLS via security_invoker
-- Previews views bypassed RLS because they ran as owner
-- =============================================

BEGIN;

DROP VIEW IF EXISTS search_results;
DROP VIEW IF EXISTS search_summary;

-- Recreate with security_invoker so RLS policies on underlying tables are enforced
CREATE OR REPLACE VIEW search_results WITH (security_invoker) AS
SELECT
    i.id AS input_id,
    i.query,
    i.user_email,
    i.ip_address,
    i.user_agent,
    i.ai_model,
    i.results_count,
    i.raw_results_count,
    i.filtered_count,
    i.created_at,
    o.id AS output_id,
    o.album_title,
    o.album_artist,
    o.album_year,
    o.album_genre,
    o.rank,
    o.is_verified,
    o.verification_source
FROM search_input i
LEFT JOIN search_output o ON o.session_id = i.id
ORDER BY i.created_at DESC, o.rank ASC;

CREATE OR REPLACE VIEW search_summary WITH (security_invoker) AS
SELECT
    i.id,
    i.query,
    i.user_email,
    i.ai_model,
    i.results_count,
    i.filtered_count,
    i.created_at,
    COUNT(o.id) AS output_count,
    ARRAY_AGG(
        o.album_title || ' by ' || o.album_artist
        ORDER BY o.rank
    ) FILTER (WHERE o.id IS NOT NULL) AS albums
FROM search_input i
LEFT JOIN search_output o ON o.session_id = i.id
GROUP BY i.id, i.query, i.user_email, i.ai_model, i.results_count, i.filtered_count, i.created_at
ORDER BY i.created_at DESC;

COMMIT;
