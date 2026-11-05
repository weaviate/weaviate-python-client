from typing import Any, Dict

import pytest

from weaviate.backup.backup import BackupListReturn, BackupStatus


def _list_entry(**overrides: Any) -> Dict[str, Any]:
    """A single item as Weaviate's ``GET /backups/{backend}`` returns it."""
    entry: Dict[str, Any] = {
        "id": "my-backup",
        "classes": ["Article"],
        "status": "SUCCESS",
        "startedAt": "2026-08-01T10:00:00.000Z",
        "completedAt": "2026-08-01T10:05:00.000Z",
        "size": 1.5,
    }
    entry.update(overrides)
    return entry


def test_list_return_exposes_incremental_base_backup_id() -> None:
    backup = BackupListReturn(**_list_entry(incremental_base_backup_id="base-backup"))

    assert backup.incremental_base_backup_id == "base-backup"
    assert backup.backup_id == "my-backup"
    assert backup.collections == ["Article"]
    assert backup.status == BackupStatus.SUCCESS


@pytest.mark.parametrize(
    "entry",
    [
        pytest.param(_list_entry(), id="field_omitted"),
        pytest.param(_list_entry(incremental_base_backup_id=None), id="field_null"),
    ],
)
def test_list_return_defaults_incremental_base_backup_id_to_none(entry: Dict[str, Any]) -> None:
    # The server omits the field for non-incremental backups, and only populates
    # it for callers it has confirmed as root, so absent must not be an error.
    assert BackupListReturn(**entry).incremental_base_backup_id is None


def test_running_backup_and_export_zero_completed_at_is_none() -> None:
    from weaviate.export.export import ExportStatusReturn

    backup = BackupListReturn(
        **_list_entry(status="STARTED", completedAt="0001-01-01T00:00:00.000Z")
    )
    assert backup.completed_at is None

    completed = BackupListReturn(
        **_list_entry(status="SUCCESS", completedAt="2026-08-01T10:05:00.000Z")
    )
    assert completed.completed_at is not None
    assert completed.completed_at.year == 2026

    export_status = ExportStatusReturn(
        id="exp1",
        backend="filesystem",
        path="/tmp/exports/exp1",
        status="TRANSFERRING",
        startedAt="2026-10-21T06:50:47.995Z",
        completedAt="0001-01-01T00:00:00.000Z",
        classes=["Article"],
    )
    assert export_status.completed_at is None
