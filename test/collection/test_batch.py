import uuid
from weaviate.collections.classes.batch import BatchObjectReturn, MAX_STORED_RESULTS


def test_batch_object_return_add() -> None:
    lhs_uuids = [uuid.uuid4() for _ in range(MAX_STORED_RESULTS)]
    lhs = BatchObjectReturn(
        _all_responses=lhs_uuids,
        elapsed_seconds=0.1,
        errors={},
        has_errors=False,
        uuids=dict(e for e in enumerate(lhs_uuids)),
    )
    rhs_uuids = [uuid.uuid4() for _ in range(2)]
    rhs = BatchObjectReturn(
        _all_responses=rhs_uuids,
        elapsed_seconds=0.1,
        errors={},
        has_errors=False,
        uuids={
            MAX_STORED_RESULTS: rhs_uuids[0],
            MAX_STORED_RESULTS + 1: rhs_uuids[1],
        },
    )
    result = lhs + rhs
    assert len(result.all_responses) == MAX_STORED_RESULTS
    assert len(result.uuids) == MAX_STORED_RESULTS
    assert result.uuids == {
        idx + len(rhs_uuids): v
        for idx, v in enumerate(lhs_uuids[len(rhs_uuids) : MAX_STORED_RESULTS] + rhs_uuids)
    }
