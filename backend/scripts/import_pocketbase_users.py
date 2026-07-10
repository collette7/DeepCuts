#!/usr/bin/env python3
"""Import exported Supabase user identities into PocketBase.

Creates one PocketBase auth record per exported user, matching each
account's original email-confirmed status. Never imports a password
hash (the export never contained one) — each account gets a random
throwaway password that nobody is told, then --send-reset-emails
triggers a real password-reset email so the migrated user sets their
own password on first login.

Idempotent: running twice does not create duplicate users — an existing
PocketBase user with the same email is left untouched and skipped.

Usage:
    POCKETBASE_URL=... POCKETBASE_ADMIN_EMAIL=... POCKETBASE_ADMIN_PASSWORD=... \\
        python scripts/import_pocketbase_users.py supabase_users_export.json [--send-reset-emails]
"""
import asyncio
import json
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.clients.pocketbase import (  # noqa: E402
    PocketBaseClient,
    PocketBaseError,
    get_pocketbase_client,
)


async def find_existing_user(client: PocketBaseClient, email: str) -> dict | None:
    existing = await client.list_records("users", filter=f'email = "{email}"')
    return existing[0] if existing else None


async def import_user(client: PocketBaseClient, record: dict, send_reset_email: bool) -> str:
    email = record["email"]

    existing = await find_existing_user(client, email)
    if existing:
        return f"SKIPPED (already exists): {email}"

    throwaway_password = secrets.token_urlsafe(24)
    try:
        created = await client.create_record("users", {
            "email": email,
            "password": throwaway_password,
            "passwordConfirm": throwaway_password,
            "verified": record["confirmed"],
        })
    except PocketBaseError as e:
        return f"FAILED to create {email}: {e}"

    if send_reset_email:
        try:
            await client.request_password_reset("users", email)
        except PocketBaseError as e:
            return f"CREATED but reset email failed for {email} (id={created['id']}): {e}"

    return f"CREATED: {email} (id={created['id']}, verified={record['confirmed']})"


async def run_import(export_path: str, send_reset_emails: bool) -> list[str]:
    with open(export_path) as f:
        export = json.load(f)

    client = get_pocketbase_client()

    results = []
    for record in export["users"]:
        result = await import_user(client, record, send_reset_emails)
        results.append(result)
        print(result)

    return results


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: import_pocketbase_users.py <export.json> [--send-reset-emails]", file=sys.stderr)
        sys.exit(1)

    export_path = sys.argv[1]
    send_reset_emails = "--send-reset-emails" in sys.argv[2:]

    results = asyncio.run(run_import(export_path, send_reset_emails))

    created = sum(1 for r in results if r.startswith("CREATED"))
    skipped = sum(1 for r in results if r.startswith("SKIPPED"))
    failed = sum(1 for r in results if r.startswith("FAILED"))
    print(f"\nDone: {created} created, {skipped} skipped, {failed} failed, {len(results)} total.")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
