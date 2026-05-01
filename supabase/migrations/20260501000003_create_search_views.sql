-- =============================================
-- Create views for easy browsing in Supabase Studio
-- =============================================

BEGIN;

-- View: search results with all output albums inline
CREATE OR REPLACE VIEW search_results AS
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

-- View: search summary (one row per search with aggregated outputs)
CREATE OR REPLACE VIEW search_summary AS
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
