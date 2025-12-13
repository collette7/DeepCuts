-- =============================================
-- Fix recommendation_sessions table
-- =============================================

-- Add missing query column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'recommendation_sessions' AND column_name = 'query'
    ) THEN
        ALTER TABLE recommendation_sessions ADD COLUMN query TEXT;
    END IF;
END $$;

-- Add other missing columns
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'recommendation_sessions' AND column_name = 'user_email'
    ) THEN
        ALTER TABLE recommendation_sessions ADD COLUMN user_email TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'recommendation_sessions' AND column_name = 'source_album'
    ) THEN
        ALTER TABLE recommendation_sessions ADD COLUMN source_album TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'recommendation_sessions' AND column_name = 'recommended_albums'
    ) THEN
        ALTER TABLE recommendation_sessions ADD COLUMN recommended_albums JSONB DEFAULT '[]'::jsonb;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'recommendation_sessions' AND column_name = 'enhancer_settings'
    ) THEN
        ALTER TABLE recommendation_sessions ADD COLUMN enhancer_settings JSONB DEFAULT '{}'::jsonb;
    END IF;
END $$;

-- Create indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_recommendation_sessions_user_email ON recommendation_sessions(user_email);
CREATE INDEX IF NOT EXISTS idx_recommendation_sessions_created_at ON recommendation_sessions(created_at DESC);

-- =============================================
-- Create app_settings table for runtime configuration
-- =============================================

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default settings
INSERT INTO app_settings (key, value, description) VALUES
    ('active_model', 'claude-3-haiku-20240307', 'The AI model to use for recommendations')
ON CONFLICT (key) DO NOTHING;

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_app_settings_key ON app_settings(key);

-- Trigger to update updated_at on changes
CREATE OR REPLACE FUNCTION update_app_settings_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS app_settings_updated_at ON app_settings;
CREATE TRIGGER app_settings_updated_at
    BEFORE UPDATE ON app_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_app_settings_timestamp();
