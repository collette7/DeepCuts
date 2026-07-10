#!/usr/bin/env python3
"""Export Supabase auth user identities for migration to PocketBase.

Exports only the identity metadata needed to recreate accounts — id,
email, and confirmation status — via Supabase's GoTrue admin REST API.
That API never returns password hashes or tokens, so none end up in the
export file either.

Usage:
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... \\
        python scripts/export_supabase_users.py [output_path]
"""
import json
import os
import sys
from datetime import UTC, datetime

import httpx


def fetch_users(supabase_url: str, service_role_key: str) -> list[dict]:
    response = httpx.get(
        f"{supabase_url}/auth/v1/admin/users",
        headers={
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
        },
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json().get("users", [])


def to_export_record(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "confirmed": user.get("email_confirmed_at") is not None,
        "created_at": user.get("created_at"),
        "last_sign_in_at": user.get("last_sign_in_at"),
    }


def main() -> None:
    supabase_url = os.getenv("SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY")

    if not supabase_url or not service_role_key:
        print("ERROR: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY", file=sys.stderr)
        sys.exit(1)

    output_path = sys.argv[1] if len(sys.argv) > 1 else "supabase_users_export.json"

    users = fetch_users(supabase_url, service_role_key)
    records = [to_export_record(u) for u in users]

    export = {
        "exported_at": datetime.now(UTC).isoformat(),
        "source": supabase_url,
        "count": len(records),
        "users": records,
    }

    with open(output_path, "w") as f:
        json.dump(export, f, indent=2)

    print(f"Exported {len(records)} user(s) to {output_path}")
    unconfirmed = [r["email"] for r in records if not r["confirmed"]]
    if unconfirmed:
        print(
            f"WARNING: {len(unconfirmed)} unconfirmed account(s) — review before import: "
            f"{', '.join(unconfirmed)}"
        )


if __name__ == "__main__":
    main()
