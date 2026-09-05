#!/usr/bin/env python3
"""Import legacy Supabase albums and favorites into PocketBase.

The import maps users by normalized email because PocketBase user IDs differ
from Supabase IDs. The command is a dry run unless ``--apply`` is present.

Usage:
    POCKETBASE_URL=... POCKETBASE_ADMIN_EMAIL=... POCKETBASE_ADMIN_PASSWORD=... \
        python scripts/import_pocketbase_favorites.py export.json [--apply]
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.clients.pocketbase import PocketBaseClient, get_pocketbase_client  # noqa: E402

ALBUM_FIELDS = (
    "title",
    "artist",
    "spotify_id",
    "discogs_id",
    "genre",
    "mood",
    "release_year",
    "cover_url",
    "spotify_preview_url",
    "spotify_url",
)


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def album_key(record: dict) -> tuple[str, str]:
    return (record["title"].strip().casefold(), record["artist"].strip().casefold())


def album_payload(record: dict) -> dict:
    return {field: record[field] for field in ALBUM_FIELDS if record.get(field) not in (None, "")}


async def migrate_export(
    client: PocketBaseClient,
    export: dict,
    *,
    dry_run: bool,
) -> dict[str, int]:
    stats = {
        "albums_created": 0,
        "albums_existing": 0,
        "favorites_created": 0,
        "favorites_existing": 0,
        "favorites_skipped": 0,
    }

    users_by_old_id = {
        record["id"]: normalize_email(record["email"])
        for record in export.get("users", [])
        if record.get("id") and record.get("email")
    }
    pocketbase_users = await client.list_all_records("users")
    user_ids_by_email = {
        normalize_email(record["email"]): record["id"]
        for record in pocketbase_users
        if record.get("email")
    }

    existing_albums = await client.list_all_records("albums")
    album_ids_by_key = {album_key(record): record["id"] for record in existing_albums}
    album_ids_by_old_id: dict[str, str] = {}

    for record in export.get("albums", []):
        key = album_key(record)
        album_id = album_ids_by_key.get(key)
        if album_id:
            stats["albums_existing"] += 1
        else:
            stats["albums_created"] += 1
            if dry_run:
                album_id = f"dry-run:{record['id']}"
            else:
                created = await client.create_record("albums", album_payload(record))
                album_id = created["id"]
            album_ids_by_key[key] = album_id
        album_ids_by_old_id[record["id"]] = album_id

    existing_favorites = await client.list_all_records("favorites")
    favorite_pairs = {
        (record.get("user"), record.get("album")) for record in existing_favorites
    }

    for record in export.get("favorites", []):
        email = users_by_old_id.get(record.get("user_id"))
        user_id = user_ids_by_email.get(email) if email else None
        album_id = album_ids_by_old_id.get(record.get("album_id"))
        if not user_id or not album_id:
            stats["favorites_skipped"] += 1
            continue

        pair = (user_id, album_id)
        if pair in favorite_pairs:
            stats["favorites_existing"] += 1
            continue

        payload = {"user": user_id, "album": album_id}
        source_album_id = album_ids_by_old_id.get(record.get("source_album_id"))
        if source_album_id:
            payload["source_album"] = source_album_id
        if record.get("reasoning"):
            payload["reasoning"] = record["reasoning"]

        stats["favorites_created"] += 1
        if not dry_run:
            await client.create_record("favorites", payload)
        favorite_pairs.add(pair)

    return stats


async def run_import(export_path: str, *, dry_run: bool) -> dict[str, int]:
    with open(export_path) as input_file:
        export = json.load(input_file)
    return await migrate_export(get_pocketbase_client(), export, dry_run=dry_run)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: import_pocketbase_favorites.py <export.json> [--apply]", file=sys.stderr)
        sys.exit(1)

    dry_run = "--apply" not in sys.argv[2:]
    stats = asyncio.run(run_import(sys.argv[1], dry_run=dry_run))
    mode = "DRY RUN" if dry_run else "APPLIED"
    print(f"{mode}: {json.dumps(stats, sort_keys=True)}")


if __name__ == "__main__":
    main()
