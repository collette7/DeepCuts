import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from export_supabase_favorites import build_export  # noqa: E402
from import_pocketbase_favorites import migrate_export  # noqa: E402


class FakePocketBaseClient:
    def __init__(self):
        self.records = {
            "users": [{"id": "pb-user-1", "email": "Listener@DeepCuts.Casa"}],
            "albums": [],
            "favorites": [],
        }

    async def list_all_records(self, collection: str) -> list[dict]:
        return list(self.records[collection])

    async def create_record(self, collection: str, data: dict) -> dict:
        record = {"id": f"{collection}-{len(self.records[collection]) + 1}", **data}
        self.records[collection].append(record)
        return record


def sample_export() -> dict:
    return build_export(
        users=[{"id": "old-user-1", "email": "listener@deepcuts.casa"}],
        albums=[
            {
                "id": "old-album-1",
                "title": "OK Computer",
                "artist": "Radiohead",
                "genre": "Alternative Rock",
            }
        ],
        favorites=[
            {
                "id": "old-favorite-1",
                "user_id": "old-user-1",
                "album_id": "old-album-1",
                "source_album_id": None,
                "reasoning": "A saved recommendation",
            }
        ],
    )


def test_export_contains_only_migration_data():
    export = sample_export()

    serialized = json.dumps(export)
    assert export["counts"] == {"users": 1, "albums": 1, "favorites": 1}
    assert "password" not in serialized
    assert "token" not in serialized


async def test_import_maps_users_by_email_and_preserves_reasoning():
    client = FakePocketBaseClient()

    stats = await migrate_export(client, sample_export(), dry_run=False)

    assert stats["albums_created"] == 1
    assert stats["favorites_created"] == 1
    assert client.records["favorites"] == [
        {
            "id": "favorites-1",
            "user": "pb-user-1",
            "album": "albums-1",
            "reasoning": "A saved recommendation",
        }
    ]


async def test_import_is_idempotent():
    client = FakePocketBaseClient()
    export = sample_export()

    await migrate_export(client, export, dry_run=False)
    stats = await migrate_export(client, export, dry_run=False)

    assert stats["albums_existing"] == 1
    assert stats["favorites_existing"] == 1
    assert len(client.records["albums"]) == 1
    assert len(client.records["favorites"]) == 1


async def test_import_skips_favorite_when_user_was_not_migrated():
    client = FakePocketBaseClient()
    client.records["users"] = []

    stats = await migrate_export(client, sample_export(), dry_run=False)

    assert stats["albums_created"] == 1
    assert stats["favorites_skipped"] == 1
    assert client.records["favorites"] == []


async def test_dry_run_does_not_write_records():
    client = FakePocketBaseClient()

    stats = await migrate_export(client, sample_export(), dry_run=True)

    assert stats["albums_created"] == 1
    assert stats["favorites_created"] == 1
    assert client.records["albums"] == []
    assert client.records["favorites"] == []
