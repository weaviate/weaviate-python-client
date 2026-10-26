from datetime import datetime, timezone
from typing import Any, Dict

from weaviate.export.export import ExportStatus, ExportStatusReturn


def _status(**overrides: Any) -> Dict[str, Any]:
    """An export status as Weaviate's ``GET /export/{backend}/{id}`` returns it."""
    status: Dict[str, Any] = {
        "id": "my-export",
        "backend": "filesystem",
        "path": "/tmp/exports/my-export",
        "classes": ["Article"],
        "status": "SUCCESS",
        "startedAt": "2026-08-01T10:00:00.000Z",
        "completedAt": "2026-08-01T10:05:00.000Z",
        "tookInMs": 300000,
    }
    status.update(overrides)
    return status


def test_status_return_maps_unset_completed_at_to_none() -> None:
    # A running export reports Go's zero time as its completedAt.
    status = ExportStatusReturn(
        **_status(status="TRANSFERRING", completedAt="0001-01-01T00:00:00.000Z", tookInMs=None)
    )

    assert status.status == ExportStatus.TRANSFERRING
    assert status.completed_at is None


def test_status_return_keeps_set_completed_at() -> None:
    status = ExportStatusReturn(**_status())

    assert status.completed_at == datetime(2026, 8, 1, 10, 5, tzinfo=timezone.utc)
