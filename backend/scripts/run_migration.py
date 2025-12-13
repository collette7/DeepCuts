#!/usr/bin/env python3
"""
Run database migrations via Supabase REST API.

Since we can't execute raw SQL via the REST API, this script creates the
necessary tables using the Supabase client methods.

Usage:
    cd backend
    python scripts/run_migration.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client


def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
        sys.exit(1)

    print(f"Connecting to Supabase: {url}")
    client = create_client(url, key)

    # Test 1: Check if app_settings table exists
    print("\n1. Checking app_settings table...")
    try:
        result = client.table('app_settings').select('key').limit(1).execute()
        print(f"   ✅ app_settings table exists ({len(result.data)} rows)")

        # Check if active_model setting exists
        model_result = client.table('app_settings').select('*').eq('key', 'active_model').execute()
        if model_result.data:
            print(f"   ✅ active_model setting exists: {model_result.data[0]['value']}")
        else:
            # Insert default
            print("   ⚠️  active_model setting missing, creating...")
            client.table('app_settings').insert({
                'key': 'active_model',
                'value': 'claude-3-haiku-20240307',
                'description': 'The AI model to use for recommendations'
            }).execute()
            print("   ✅ Created active_model setting")

    except Exception as e:
        if "does not exist" in str(e).lower() or "PGRST" in str(e):
            print("   ❌ app_settings table does not exist")
            print("\n   Please run this SQL in Supabase Dashboard > SQL Editor:")
            print_app_settings_sql()
        else:
            print(f"   ❌ Error: {e}")

    # Test 2: Check recommendation_sessions table
    print("\n2. Checking recommendation_sessions table...")
    try:
        result = client.table('recommendation_sessions').select('id, query').limit(1).execute()
        print("   ✅ recommendation_sessions table exists with 'query' column")
    except Exception as e:
        if "query" in str(e).lower():
            print("   ❌ 'query' column missing from recommendation_sessions")
            print("\n   Please run this SQL in Supabase Dashboard > SQL Editor:")
            print_fix_sessions_sql()
        elif "does not exist" in str(e).lower():
            print("   ❌ recommendation_sessions table does not exist")
            print("\n   Please run this SQL in Supabase Dashboard > SQL Editor:")
            print_create_sessions_sql()
        else:
            print(f"   ❌ Error: {e}")

    print("\n✨ Migration check complete!")


def print_app_settings_sql():
    sql = """
-- Create app_settings table
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default model setting
INSERT INTO app_settings (key, value, description) VALUES
    ('active_model', 'claude-3-haiku-20240307', 'The AI model to use for recommendations')
ON CONFLICT (key) DO NOTHING;
"""
    print(sql)


def print_fix_sessions_sql():
    sql = """
-- Add missing query column to recommendation_sessions
ALTER TABLE recommendation_sessions ADD COLUMN IF NOT EXISTS query TEXT;
ALTER TABLE recommendation_sessions ADD COLUMN IF NOT EXISTS user_email TEXT;
ALTER TABLE recommendation_sessions ADD COLUMN IF NOT EXISTS source_album TEXT;
ALTER TABLE recommendation_sessions ADD COLUMN IF NOT EXISTS recommended_albums JSONB DEFAULT '[]'::jsonb;
ALTER TABLE recommendation_sessions ADD COLUMN IF NOT EXISTS enhancer_settings JSONB DEFAULT '{}'::jsonb;
"""
    print(sql)


def print_create_sessions_sql():
    sql = """
-- Create recommendation_sessions table
CREATE TABLE IF NOT EXISTS recommendation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT,
    user_email TEXT,
    source_album TEXT,
    recommended_albums JSONB DEFAULT '[]'::jsonb,
    enhancer_settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""
    print(sql)


if __name__ == "__main__":
    main()
