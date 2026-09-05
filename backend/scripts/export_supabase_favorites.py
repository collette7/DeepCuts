#!/usr/bin/env python3
"""Export legacy Supabase albums and favorites for PocketBase migration.

The export contains public user email mappings, album metadata, and favorite
relations. It never exports auth tokens, password hashes, or credentials.

Usage:
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \
        python scripts/export_supabase_favorites.py [output_path]
"""

import json
import os
import sys
from datetime import UTC, datetime

import httpx


def fetch_table(
    client: httpx.Client,
    supabase_url: str,
    service_role_key: str,
    table: str,
    fields: str,
) -> list[dict]:
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }
    records: list[dict] = []
    offset = 0
    page_size = 1000

    while True:
        response = client.get(
            f"{supabase_url.rstrip('/')}/rest/v1/{table}",
            headers=headers,
            params={"select": fields, "limit": page_size, "offset": offset},
        )
        response.raise_for_status()
        page = response.json()
        records.extend(page)
        if len(page) < page_size:
            return records
        offset += page_size


def build_export(users: list[dict], albums: list[dict], favorites: list[dict]) -> dict:
    return {
        "version": 1,
        "exported_at": datetime.now(UTC).isoformat(),
        "source": "supabase",
        "counts": {
            "users": len(users),
            "albums": len(albums),
            "favorites": len(favorites),
        },
        "users": users,
        "albums": albums,
        "favorites": favorites,
    }


def main() -> None:
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv(
        "SUPABASE_SECRET_KEY"
    )
    if not supabase_url or not service_role_key:
        print(
            "ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY",
            file=sys.stderr,
        )
        sys.exit(1)

    output_path = sys.argv[1] if len(sys.argv) > 1 else "supabase_favorites_export.json"
    with httpx.Client(timeout=30.0) as client:
        users = fetch_table(client, supabase_url, service_role_key, "users", "id,email")
        albums = fetch_table(
            client,
            supabase_url,
            service_role_key,
            "albums",
            (
                "id,title,artist,spotify_id,discogs_id,genre,mood,release_year,"
                "cover_url,spotify_preview_url,spotify_url"
            ),
        )
        favorites = fetch_table(
            client,
            supabase_url,
            service_role_key,
            "favorites",
            "id,user_id,album_id,source_album_id,reasoning,saved_at",
        )

    export = build_export(users, albums, favorites)
    with open(output_path, "w") as output_file:
        json.dump(export, output_file, indent=2)

    counts = export["counts"]
    print(
        f"Exported {counts['users']} users, {counts['albums']} albums, "
        f"and {counts['favorites']} favorites to {output_path}"
    )


if __name__ == "__main__":
    main()
