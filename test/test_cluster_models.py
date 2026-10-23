from typing import Optional

import pytest

from weaviate.outputs.replication import ReplicateOperationStatus, ReplicateOperationState


@pytest.mark.parametrize(
    ("errors", "expected"),
    [
        (["legacy error"], ["legacy error"]),
        ([{"message": "structured error", "whenErroredUnixMs": 123}], ["structured error"]),
        ([{"whenErroredUnixMs": 123}], [""]),
        ([], []),
        (None, []),
        (
            [
                "legacy error",
                {"message": "structured error", "whenErroredUnixMs": 123},
                {"whenErroredUnixMs": 456},
            ],
            ["legacy error", "structured error", ""],
        ),
    ],
)
def test_replicate_operation_status_parses_error_messages(
    errors: Optional[list[object]], expected: list[str]
) -> None:
    status = ReplicateOperationStatus._from_weaviate(
        {"state": ReplicateOperationState.CANCELLED.value, "errors": errors}
    )

    assert status.errors == expected
