#!/usr/bin/env python3
"""Script to set up or fix database schema."""

import os
import sys

# Add the backend directory to path
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

    # Check if table exists
    print("\nChecking recommendation_sessions table...")
    try:
        result = client.table('recommendation_sessions').select('id').limit(1).execute()
        print(f"✅ Table exists with {len(result.data)} rows")

        # Try to check if query column exists by selecting it
        try:
            result = client.table('recommendation_sessions').select('query').limit(1).execute()
            print("✅ 'query' column exists")
        except Exception as e:
            if "query" in str(e).lower():
                print(f"❌ 'query' column missing: {e}")
            else:
                print(f"⚠️ Column check error: {e}")

    except Exception as e:
        error_str = str(e)
        if "does not exist" in error_str.lower():
            print("❌ Table does not exist")
        elif "PGRST" in error_str:
            print(f"❌ Schema issue: {e}")
        else:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
