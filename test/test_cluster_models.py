import pytest

from weaviate.outputs.replication import ReplicateOperationStatus, ReplicateOperationState


@pytest.mark.parametrize(
    "errors",
    [
        ["copy failed"],
        [{"message": "copy failed", "whenErroredUnixMs": 123}],
    ],
)
def test_replicate_operation_status_parses_error_messages(errors: list[object]) -> None:
    status = ReplicateOperationStatus._from_weaviate(
        {"state": ReplicateOperationState.CANCELLED.value, "errors": errors}
    )

    assert status.errors == ["copy failed"]
