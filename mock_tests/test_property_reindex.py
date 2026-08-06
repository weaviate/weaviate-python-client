import json
import warnings
from typing import Generator, Union

import grpc
import pytest
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC
from weaviate.collections.config import executor as reindex_executor
from weaviate.collections.classes.config import (
    BM25Algorithm,
    DataType,
    InvertedIndexState,
    InvertedIndexTaskStatus,
    InvertedIndexType,
    Tokenization,
)
from weaviate.exceptions import (
    ReindexCanceledError,
    ReindexFailedError,
    ReindexTimeoutError,
    WeaviateUnsupportedFeatureError,
)

COLLECTION = "TestCollection"
SCHEMA_PATH = f"/v1/schema/{COLLECTION}"
INDEXES_PATH = f"{SCHEMA_PATH}/indexes"
TASK_ID = "TestCollection:change-tokenization:name:ab3f"


def _indexes(index_name: str = "searchable", **fields: object) -> dict:
    """A realistic GET /schema/{class}/indexes payload wrapping a single index entry.

    Pass wire fields, e.g. status="ready"/"indexing"/"failed", tokenization, targetTokenization,
    algorithm, targetAlgorithm, progress, taskId. A plain ready entry carries NO taskId.
    """
    entry: dict = {"type": index_name, **fields}
    return {
        "collection": COLLECTION,
        "properties": [{"name": "name", "dataType": "text", "indexes": [entry]}],
    }


def _no_index() -> dict:
    """An /indexes payload where the target property/index entry is absent (vanished / missing)."""
    return {"collection": COLLECTION, "properties": []}


@pytest.fixture(scope="function")
def fast_poll(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shrink the reindex poll interval so stall/grace tests run against the REAL thresholds fast."""
    monkeypatch.setattr(reindex_executor, "_REINDEX_POLL_INTERVAL_SECONDS", 0.005)


@pytest.fixture(scope="function")
def weaviate_139_mock(ready_mock: HTTPServer) -> Generator[HTTPServer, None, None]:
    """A mock server advertising Weaviate 1.39.0, which supports runtime property reindexing."""
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": "1.39.0"})
    ready_mock.expect_request("/v1/nodes").respond_with_json(
        {"nodes": [{"gitHash": "ABC", "status": "HEALTHY"}]}
    )
    ready_mock.expect_request("/v1/.well-known/openid-configuration").respond_with_response(
        Response(json.dumps({}), status=404)
    )
    yield ready_mock


@pytest.fixture(scope="function")
def client_139(
    weaviate_139_mock: HTTPServer, start_grpc_server: grpc.Server
) -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local(port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC)
    yield client
    client.close()


def test_update_property_index_started(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A single tokenization change is a valid PUT body (the server allows at most one change)."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "word"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)

    task = client_139.collections.use(COLLECTION).config.update_property_index(
        "name",
        "searchable",
        tokenization=Tokenization.WORD,
    )
    assert task.task_id == TASK_ID
    assert task.status == InvertedIndexTaskStatus.STARTED
    weaviate_139_mock.check_assertions()


def test_update_property_index_algorithm_only(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """An algorithm-only change is a valid single-change PUT; the enum serializes to its wire value."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"algorithm": "blockmax"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)

    task = client_139.collections.use(COLLECTION).config.update_property_index(
        "name",
        "searchable",
        algorithm=BM25Algorithm.BLOCKMAX,
    )
    assert task.task_id == TASK_ID
    assert task.status == InvertedIndexTaskStatus.STARTED
    weaviate_139_mock.check_assertions()


def test_update_property_index_no_op(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "word"},
    ).respond_with_json({"status": "NO_OP"}, status=200)

    task = client_139.collections.use(COLLECTION).config.update_property_index(
        "name", "searchable", tokenization=Tokenization.WORD
    )
    assert task.task_id is None
    assert task.status == InvertedIndexTaskStatus.NO_OP
    weaviate_139_mock.check_assertions()


def test_update_property_index_range_filters_with_tenants(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A rangeFilters creation sends an empty body and encodes tenants as a csv query param."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/age/index/rangeFilters",
        method="PUT",
        query_string={"tenants": "tenant1,tenant2"},
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)

    task = client_139.collections.use(COLLECTION).config.update_property_index(
        "age", "rangeFilters", tenants=["tenant1", "tenant2"]
    )
    assert task.task_id == TASK_ID
    assert task.status == InvertedIndexTaskStatus.STARTED
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_tokenization_change(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A tokenization change converges when a ready entry reports the NEW tokenization.

    The in-flight entry (indexing, target_tokenization=new) must not be treated as done; only the
    ready entry carrying the new tokenization returns.
    """
    weaviate_139_mock.expect_ordered_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    # poll 1: migration in flight (still old tokenization, target set, carries our taskId)
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(
            status="indexing",
            progress=0.5,
            taskId=TASK_ID,
            tokenization="word",
            targetTokenization="field",
        )
    )
    # poll 2: ready with the new tokenization (a plain ready entry carries no taskId)
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", tokenization="field")
    )

    status = client_139.collections.use(COLLECTION).config.update_property_index(
        "name", "searchable", tokenization=Tokenization.FIELD, wait_for_completion=True
    )
    assert status.type == "searchable"
    assert status.state == InvertedIndexState.READY
    assert status.tokenization == Tokenization.FIELD
    assert status.task_id is None  # a ready entry carries no task id
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_stale_pre_flip_not_accepted(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A ready entry with the OLD tokenization is the stale pre-flip state and must not return.

    Regression pin for finding #1: the wait keeps polling until the ready entry reports the
    requested (new) tokenization. If a stale-old ready were accepted, the assertion below fails.
    """
    weaviate_139_mock.expect_ordered_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    # poll 1: a ready entry still on the OLD tokenization (pre-flip) - must NOT be accepted
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", tokenization="word")
    )
    # poll 2: ready on the NEW tokenization
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", tokenization="field")
    )

    status = client_139.collections.use(COLLECTION).config.update_property_index(
        "name", "searchable", tokenization=Tokenization.FIELD, wait_for_completion=True
    )
    assert status.tokenization == Tokenization.FIELD
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_finalize_window_not_done(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """Regression pin for finding #1: indexing@progress=1.0 is NOT done, only ready is.

    The finalize window shows indexing at progress 1.0 with the target still set; the wait must
    keep polling and return only on the subsequent ready poll.
    """
    weaviate_139_mock.expect_ordered_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    # poll 1: finalize window - indexing at progress 1.0 with the target still set
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(
            status="indexing",
            progress=1.0,
            taskId=TASK_ID,
            tokenization="word",
            targetTokenization="field",
        )
    )
    # poll 2: flipped to ready on the new tokenization
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", tokenization="field")
    )

    status = client_139.collections.use(COLLECTION).config.update_property_index(
        "name", "searchable", tokenization=Tokenization.FIELD, wait_for_completion=True
    )
    assert status.state == InvertedIndexState.READY
    assert status.tokenization == Tokenization.FIELD
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_algorithm_change(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """An algorithm change (wand -> blockmax) converges on a ready entry reporting blockmax."""
    weaviate_139_mock.expect_ordered_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"algorithm": "blockmax"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    # poll 1: in-flight, still wand with the target set
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="indexing", taskId=TASK_ID, algorithm="wand", targetAlgorithm="blockmax")
    )
    # poll 2: ready on blockmax
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", algorithm="blockmax")
    )

    status = client_139.collections.use(COLLECTION).config.update_property_index(
        "name", "searchable", algorithm=BM25Algorithm.BLOCKMAX, wait_for_completion=True
    )
    assert status.algorithm is BM25Algorithm.BLOCKMAX
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_create_range_filters(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A create with an empty body converges as soon as the index exists and is ready."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/age/index/rangeFilters",
        method="PUT",
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(
        {
            "collection": COLLECTION,
            "properties": [
                {
                    "name": "age",
                    "dataType": "int",
                    "indexes": [{"type": "rangeFilters", "status": "ready"}],
                }
            ],
        }
    )

    status = client_139.collections.use(COLLECTION).config.update_property_index(
        "age", "rangeFilters", wait_for_completion=True
    )
    assert status.type == "rangeFilters"
    assert status.state == InvertedIndexState.READY
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_no_op(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A NO_OP submit returns the current status via a single get_property_indexes fetch."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "word"},
    ).respond_with_json({"status": "NO_OP"}, status=200)
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", tokenization="word")
    )

    status = client_139.collections.use(COLLECTION).config.update_property_index(
        "name", "searchable", tokenization=Tokenization.WORD, wait_for_completion=True
    )
    assert status.state == InvertedIndexState.READY
    assert status.tokenization == Tokenization.WORD
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_timeout(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """An index that never reaches ready past the timeout raises ReindexTimeoutError."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    # /indexes always reports the migration still in flight
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(
            status="indexing",
            progress=0.3,
            taskId=TASK_ID,
            tokenization="word",
            targetTokenization="field",
        )
    )

    with pytest.raises(ReindexTimeoutError):
        client_139.collections.use(COLLECTION).config.update_property_index(
            "name",
            "searchable",
            tokenization=Tokenization.FIELD,
            wait_for_completion=True,
            timeout=0.5,
        )
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_stall_vanished_after_active(
    fast_poll: None, weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A task seen active then vanishing from /indexes is bounded (timeout=None must not hang)."""
    weaviate_139_mock.expect_ordered_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    # poll 1: our task is active (resets the stall counter) ...
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="indexing", taskId=TASK_ID, tokenization="word", targetTokenization="field")
    )
    # ... then the entry vanishes for good (server fault) - bounded by the no-progress guard
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(_no_index())

    with pytest.raises(ReindexTimeoutError, match="did not progress"):
        client_139.collections.use(COLLECTION).config.update_property_index(
            "name", "searchable", tokenization=Tokenization.FIELD, wait_for_completion=True
        )
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_stall_never_appears(
    fast_poll: None, weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """An entry absent from the very first poll (never appears) is bounded, not an infinite wait."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(_no_index())

    with pytest.raises(ReindexTimeoutError, match="did not progress"):
        client_139.collections.use(COLLECTION).config.update_property_index(
            "name", "searchable", tokenization=Tokenization.FIELD, wait_for_completion=True
        )
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_stall_ready_on_old_config(
    fast_poll: None, weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A ready entry stuck on the OLD tokenization forever is bounded by the no-progress guard."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    # ready, but never flips to the requested tokenization (server never completed the swap)
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", tokenization="word")
    )

    with pytest.raises(ReindexTimeoutError, match="did not progress"):
        client_139.collections.use(COLLECTION).config.update_property_index(
            "name", "searchable", tokenization=Tokenization.FIELD, wait_for_completion=True
        )
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_healthy_long_not_cut_off(
    fast_poll: None, weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A legitimately long reindex (indexing for well past the stall bound) must NOT be cut off.

    Proves the no-progress guard never trips a healthy migration: each indexing poll (including the
    finalize window at progress 1.0) resets the stall counter, so it completes normally on ready.
    """
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)

    # stay INDEXING for well beyond the stall threshold, then flip to ready on the new tokenization
    indexing_polls = reindex_executor._REINDEX_STALL_POLLS + 5
    state = {"n": 0}

    def handler(request: object) -> Response:
        state["n"] += 1
        if state["n"] <= indexing_polls:
            # include the finalize window (progress 1.0) on the last indexing poll
            progress = 1.0 if state["n"] == indexing_polls else 0.5
            body = _indexes(
                status="indexing",
                progress=progress,
                taskId=TASK_ID,
                tokenization="word",
                targetTokenization="field",
            )
        else:
            body = _indexes(status="ready", tokenization="field")
        return Response(json.dumps(body), content_type="application/json")

    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_handler(handler)

    status = client_139.collections.use(COLLECTION).config.update_property_index(
        "name", "searchable", tokenization=Tokenization.FIELD, wait_for_completion=True
    )
    assert status.state == InvertedIndexState.READY
    assert status.tokenization == Tokenization.FIELD
    assert state["n"] > reindex_executor._REINDEX_STALL_POLLS  # actually polled past the bound
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_no_op_missing_entry(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A NO_OP whose index is missing from /indexes raises a clear error, not a bare assert."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "word"},
    ).respond_with_json({"status": "NO_OP"}, status=200)
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(_no_index())

    with pytest.raises(ReindexFailedError, match="NO_OP"):
        client_139.collections.use(COLLECTION).config.update_property_index(
            "name", "searchable", tokenization=Tokenization.WORD, wait_for_completion=True
        )
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_enum_vs_str_convergence(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """Convergence compares by wire value, so the parsed Tokenization enum matches the wire string."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    # entry.tokenization parses to Tokenization.FIELD (enum); expected is the wire string "field"
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", tokenization="field")
    )

    status = client_139.collections.use(COLLECTION).config.update_property_index(
        "name", "searchable", tokenization=Tokenization.FIELD, wait_for_completion=True
    )
    assert status.tokenization is Tokenization.FIELD
    weaviate_139_mock.check_assertions()


def test_update_property_index_tolerant_task_status(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """Unknown task statuses pass through as raw strings (the spec declares the field open-vocabulary)."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "word"},
    ).respond_with_json({"taskId": TASK_ID, "status": "SOMETHING_NEW"}, status=202)

    task = client_139.collections.use(COLLECTION).config.update_property_index(
        "name", InvertedIndexType.SEARCHABLE, tokenization=Tokenization.WORD
    )
    assert task.task_id == TASK_ID
    assert task.status == "SOMETHING_NEW"
    assert not isinstance(task.status, InvertedIndexTaskStatus)
    weaviate_139_mock.check_assertions()


def test_update_property_index_bare_str_tenant(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A bare string tenant is normalized to a single csv value, not exploded into characters."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/age/index/rangeFilters",
        method="PUT",
        query_string={"tenants": "tenant1"},
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)

    task = client_139.collections.use(COLLECTION).config.update_property_index(
        "age", "rangeFilters", tenants="tenant1"
    )
    assert task.status == InvertedIndexTaskStatus.STARTED
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_raises_failed(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A failed entry belonging to our task raises ReindexFailedError naming the task id."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "word"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="failed", taskId=TASK_ID, tokenization="word")
    )

    with pytest.raises(ReindexFailedError) as e:
        client_139.collections.use(COLLECTION).config.update_property_index(
            "name", "searchable", tokenization=Tokenization.WORD, wait_for_completion=True
        )
    assert TASK_ID in str(e.value)
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_stale_failed_not_raised(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A stale failed entry with a DIFFERENT task id must not raise; the wait keeps polling.

    Regression pin: only a failed entry that belongs to our submitted task is terminal.
    """
    weaviate_139_mock.expect_ordered_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    # poll 1: a stale failed entry from a PRIOR reindex (different task id) - must NOT raise
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="failed", taskId="stale-other-task:x:y:0000", tokenization="word")
    )
    # poll 2: our migration completes to ready on the new tokenization
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", tokenization="field")
    )

    status = client_139.collections.use(COLLECTION).config.update_property_index(
        "name", "searchable", tokenization=Tokenization.FIELD, wait_for_completion=True
    )
    assert status.state == InvertedIndexState.READY
    assert status.tokenization == Tokenization.FIELD
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_raises_cancelled(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A cancelled entry belonging to our task raises ReindexCanceledError."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "word"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="cancelled", taskId=TASK_ID, tokenization="word")
    )

    with pytest.raises(ReindexCanceledError):
        client_139.collections.use(COLLECTION).config.update_property_index(
            "name", "searchable", tokenization=Tokenization.WORD, wait_for_completion=True
        )
    weaviate_139_mock.check_assertions()


def test_rebuild_property_index_wait(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A rebuild wait returns once the entry (seen active) reaches ready (best-effort)."""
    weaviate_139_mock.expect_ordered_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable/rebuild",
        method="POST",
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    # poll 1: rebuild in flight, carrying our task id
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="indexing", progress=0.5, taskId=TASK_ID, tokenization="word")
    )
    # poll 2: ready (task seen active -> best-effort completion)
    weaviate_139_mock.expect_ordered_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", tokenization="word")
    )

    status = client_139.collections.use(COLLECTION).config.rebuild_property_index(
        "name", "searchable", wait_for_completion=True
    )
    assert status.state == InvertedIndexState.READY
    weaviate_139_mock.check_assertions()


def test_rebuild_property_index_wait_fast_ready_grace(
    fast_poll: None, weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A fast rebuild whose task is never observed active returns after the (wide) ready grace."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable/rebuild",
        method="POST",
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    # the index is ready from the first poll and stays ready (no active task ever observed)
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", tokenization="word")
    )

    status = client_139.collections.use(COLLECTION).config.rebuild_property_index(
        "name", "searchable", wait_for_completion=True
    )
    assert status.state == InvertedIndexState.READY
    weaviate_139_mock.check_assertions()


def test_rebuild_property_index(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable/rebuild",
        method="POST",
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)

    task = client_139.collections.use(COLLECTION).config.rebuild_property_index(
        "name", "searchable"
    )
    assert task.task_id == TASK_ID
    assert task.status == InvertedIndexTaskStatus.STARTED
    weaviate_139_mock.check_assertions()


def test_rebuild_property_index_with_tenants(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/age/index/rangeFilters/rebuild",
        method="POST",
        query_string={"tenants": "tenant1,tenant2"},
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)

    task = client_139.collections.use(COLLECTION).config.rebuild_property_index(
        "age", "rangeFilters", tenants=["tenant1", "tenant2"]
    )
    assert task.task_id == TASK_ID
    assert task.status == InvertedIndexTaskStatus.STARTED
    weaviate_139_mock.check_assertions()


def test_cancel_property_index_task_cancelled(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable/cancel",
        method="POST",
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "CANCELLED"}, status=202)

    task = client_139.collections.use(COLLECTION).config.cancel_property_index_task(
        "name", "searchable"
    )
    assert task.task_id == TASK_ID
    assert task.status == InvertedIndexTaskStatus.CANCELLED
    weaviate_139_mock.check_assertions()


def test_cancel_property_index_task_no_op(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable/cancel",
        method="POST",
        json={},
    ).respond_with_json({"status": "NO_OP"}, status=202)

    task = client_139.collections.use(COLLECTION).config.cancel_property_index_task(
        "name", "searchable"
    )
    assert task.task_id is None
    assert task.status == InvertedIndexTaskStatus.NO_OP
    weaviate_139_mock.check_assertions()


def test_get_property_indexes(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A coupled tokenization change renders both entries with a shared taskId and progress."""
    weaviate_139_mock.expect_request(f"{SCHEMA_PATH}/indexes", method="GET").respond_with_json(
        {
            "collection": COLLECTION,
            "properties": [
                {
                    "name": "name",
                    "dataType": "text",
                    "description": "a text property",
                    "indexes": [
                        {
                            "type": "searchable",
                            "status": "indexing",
                            "progress": 0.5,
                            "taskId": TASK_ID,
                            "tokenization": "word",
                            "targetTokenization": "field",
                            "algorithm": "wand",
                            "targetAlgorithm": "blockmax",
                        },
                        {
                            "type": "filterable",
                            "status": "indexing",
                            "progress": 0.5,
                            "taskId": TASK_ID,
                            "tokenization": "word",
                            "targetTokenization": "field",
                        },
                    ],
                },
                {
                    "name": "age",
                    "dataType": "int",
                    "indexes": [{"type": "rangeFilters", "status": "ready"}],
                },
            ],
        }
    )

    indexes = client_139.collections.use(COLLECTION).config.get_property_indexes()
    assert indexes.collection == COLLECTION
    assert len(indexes.properties) == 2

    name = indexes.properties[0]
    assert name.name == "name"
    assert name.data_type == "text"
    assert name.description == "a text property"
    assert len(name.indexes) == 2
    searchable, filterable = name.indexes
    # `type` parses strictly into the InvertedIndexType enum; str-enum equality still holds
    assert searchable.type is InvertedIndexType.SEARCHABLE
    assert searchable.type == "searchable"
    assert searchable.state == InvertedIndexState.INDEXING
    assert searchable.progress == 0.5
    assert searchable.task_id == TASK_ID
    assert searchable.tokenization == Tokenization.WORD
    assert searchable.target_tokenization == Tokenization.FIELD
    # algorithm/target_algorithm parse into the BM25Algorithm enum; str-enum equality still holds
    assert searchable.algorithm is BM25Algorithm.WAND
    assert searchable.algorithm == "wand"
    assert searchable.target_algorithm is BM25Algorithm.BLOCKMAX
    assert searchable.target_algorithm == "blockmax"
    assert filterable.type == "filterable"
    assert filterable.task_id == TASK_ID  # coupled change: one task drives both entries
    assert filterable.target_tokenization == Tokenization.FIELD
    assert filterable.algorithm is None
    assert filterable.target_algorithm is None

    age = indexes.properties[1]
    assert age.name == "age"
    assert age.data_type == "int"
    assert age.description is None
    assert len(age.indexes) == 1
    assert age.indexes[0].type == "rangeFilters"
    assert age.indexes[0].state == InvertedIndexState.READY
    assert age.indexes[0].progress is None
    assert age.indexes[0].task_id is None
    assert age.indexes[0].tokenization is None

    # the nested dataclasses serialize all the way down to a JSON-compatible dict
    out = json.loads(json.dumps(indexes.to_dict()))
    assert out["collection"] == COLLECTION
    assert out["properties"][0]["indexes"][0]["taskId"] == TASK_ID
    assert out["properties"][0]["indexes"][0]["targetTokenization"] == "field"
    assert out["properties"][1]["dataType"] == "int"
    assert out["properties"][1]["indexes"][0]["state"] == "ready"

    weaviate_139_mock.check_assertions()


@pytest.mark.parametrize(
    "index_name,wire",
    [
        (InvertedIndexType.SEARCHABLE, "searchable"),
        ("searchable", "searchable"),
        (InvertedIndexType.FILTERABLE, "filterable"),
        ("filterable", "filterable"),
        (InvertedIndexType.RANGE_FILTERS, "rangeFilters"),
        ("rangeFilters", "rangeFilters"),
    ],
)
def test_update_property_index_enum_and_literal_hit_same_route(
    weaviate_139_mock: HTTPServer,
    client_139: weaviate.WeaviateClient,
    index_name: Union[InvertedIndexType, str],
    wire: str,
) -> None:
    """The enum and literal forms of index_name hit the exact same wire route."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/{wire}",
        method="PUT",
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)

    task = client_139.collections.use(COLLECTION).config.update_property_index(
        "name",
        # runtime leniency pin: raw strings must keep hitting the same route
        index_name,  # type: ignore
    )
    assert task.status == InvertedIndexTaskStatus.STARTED
    weaviate_139_mock.check_assertions()


@pytest.mark.parametrize(
    "index_name,wire",
    [
        (InvertedIndexType.SEARCHABLE, "searchable"),
        ("searchable", "searchable"),
        (InvertedIndexType.FILTERABLE, "filterable"),
        ("filterable", "filterable"),
        (InvertedIndexType.RANGE_FILTERS, "rangeFilters"),
        ("rangeFilters", "rangeFilters"),
    ],
)
def test_delete_property_index_enum_and_literal_hit_same_route(
    weaviate_139_mock: HTTPServer,
    client_139: weaviate.WeaviateClient,
    index_name: Union[InvertedIndexType, str],
    wire: str,
) -> None:
    """The enum and literal forms of index_name hit the exact same wire route."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/{wire}",
        method="DELETE",
    ).respond_with_json({}, status=200)

    assert (
        client_139.collections.use(COLLECTION).config.delete_property_index(
            "name",
            # runtime leniency pin: raw strings must keep hitting the same route
            index_name,  # type: ignore
        )
        is True
    )
    weaviate_139_mock.check_assertions()


@pytest.mark.parametrize(
    "index_name",
    [InvertedIndexType.RANGE_FILTERS, "rangeFilters"],
)
def test_rebuild_property_index_enum_and_literal_hit_same_route(
    weaviate_139_mock: HTTPServer,
    client_139: weaviate.WeaviateClient,
    index_name: Union[InvertedIndexType, str],
) -> None:
    """The enum and literal forms of index_name hit the exact same rebuild route."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/age/index/rangeFilters/rebuild",
        method="POST",
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)

    task = client_139.collections.use(COLLECTION).config.rebuild_property_index(
        "age",
        # runtime leniency pin: raw strings must keep hitting the same route
        index_name,  # type: ignore
    )
    assert task.status == InvertedIndexTaskStatus.STARTED
    weaviate_139_mock.check_assertions()


@pytest.mark.parametrize(
    "index_name",
    [InvertedIndexType.RANGE_FILTERS, "rangeFilters"],
)
def test_cancel_property_index_task_enum_and_literal_hit_same_route(
    weaviate_139_mock: HTTPServer,
    client_139: weaviate.WeaviateClient,
    index_name: Union[InvertedIndexType, str],
) -> None:
    """The enum and literal forms of index_name hit the exact same cancel route."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/age/index/rangeFilters/cancel",
        method="POST",
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "CANCELLED"}, status=202)

    task = client_139.collections.use(COLLECTION).config.cancel_property_index_task(
        "age",
        # runtime leniency pin: raw strings must keep hitting the same route
        index_name,  # type: ignore
    )
    assert task.status == InvertedIndexTaskStatus.CANCELLED
    weaviate_139_mock.check_assertions()


def test_get_property_indexes_reference_property(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """Reference properties carry the target collection name as dataType and still parse."""
    weaviate_139_mock.expect_request(f"{SCHEMA_PATH}/indexes", method="GET").respond_with_json(
        {
            "collection": COLLECTION,
            "properties": [
                {
                    "name": "title",
                    "dataType": "text",
                    "indexes": [{"type": "searchable", "status": "ready", "tokenization": "word"}],
                },
                {
                    "name": "ofArticle",
                    "dataType": "Article",
                    "indexes": [{"type": "filterable", "status": "ready"}],
                },
            ],
        }
    )

    indexes = client_139.collections.use(COLLECTION).config.get_property_indexes()
    title, ref = indexes.properties
    # primitive values match the DataType str-enum
    assert title.data_type == DataType.TEXT
    # reference properties carry the qualified target collection name instead
    assert ref.name == "ofArticle"
    assert ref.data_type == "Article"
    assert ref.indexes[0].type == "filterable"

    out = json.loads(json.dumps(indexes.to_dict()))
    assert out["properties"][1]["dataType"] == "Article"

    weaviate_139_mock.check_assertions()


def test_get_property_indexes_tolerant_algorithm(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """An unknown BM25 algorithm passes through as a raw string without raising."""
    weaviate_139_mock.expect_request(f"{SCHEMA_PATH}/indexes", method="GET").respond_with_json(
        {
            "collection": COLLECTION,
            "properties": [
                {
                    "name": "name",
                    "dataType": "text",
                    "indexes": [
                        {
                            "type": "searchable",
                            "status": "indexing",
                            "algorithm": "wand",
                            "targetAlgorithm": "future_bm25",
                        }
                    ],
                }
            ],
        }
    )

    entry = (
        client_139.collections.use(COLLECTION)
        .config.get_property_indexes()
        .properties[0]
        .indexes[0]
    )
    assert entry.algorithm is BM25Algorithm.WAND
    assert entry.target_algorithm == "future_bm25"
    assert not isinstance(entry.target_algorithm, BM25Algorithm)
    weaviate_139_mock.check_assertions()


def test_delete_property_index_surfaces_server_message(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A DELETE rejection surfaces the server's cause behind a neutral prefix.

    The 422 mutation guard (in-flight reindex task) carries an actionable server message;
    the client prefix must only name the failed operation, not assert a cause.
    """
    server_message = "cannot delete index: a reindex task is in progress for property 'name'"
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="DELETE",
    ).respond_with_json({"error": [{"message": server_message}]}, status=422)

    with pytest.raises(weaviate.exceptions.UnexpectedStatusCodeError) as e:
        client_139.collections.use(COLLECTION).config.delete_property_index("name", "searchable")
    assert e.value.status_code == 422
    assert "Property index may not have been deleted." in e.value.message
    assert server_message in e.value.message
    assert "may not exist" not in e.value.message
    weaviate_139_mock.check_assertions()


def test_delete_property_index_string_deprecation_warning(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """A raw-string index_name on delete_property_index warns; the enum form does not."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="DELETE",
    ).respond_with_json({}, status=200)

    config = client_139.collections.use(COLLECTION).config
    with pytest.warns(DeprecationWarning, match="Dep030"):
        assert config.delete_property_index("name", "searchable") is True

    # the InvertedIndexType form is the supported path and must not warn
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert config.delete_property_index("name", InvertedIndexType.SEARCHABLE) is True
    weaviate_139_mock.check_assertions()


def test_property_reindex_invalid_input(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """Invalid argument types raise WeaviateInvalidInputError before any request is sent."""
    config = client_139.collections.use(COLLECTION).config

    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        config.update_property_index("age", "rangeFilters", tenants=123)  # type: ignore
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        config.rebuild_property_index("age", "rangeFilters", tenants=[1, 2])  # type: ignore
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        config.cancel_property_index_task(123, "searchable")  # type: ignore
    weaviate_139_mock.check_assertions()


def test_update_property_index_rejects_wand_algorithm(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """5c: WAND is never a valid target; both the enum and the wire string raise."""
    config = client_139.collections.use(COLLECTION).config
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError, match="not a valid target"):
        config.update_property_index("name", "searchable", algorithm=BM25Algorithm.WAND)
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError, match="not a valid target"):
        config.update_property_index("name", "searchable", algorithm="wand")  # type: ignore
    weaviate_139_mock.check_assertions()


def test_update_property_index_rejects_garbage_config_types(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    """5d: non-str/enum tokenization or algorithm is rejected with a clear input error."""
    config = client_139.collections.use(COLLECTION).config
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        config.update_property_index("name", "searchable", tokenization=123)  # type: ignore
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        config.update_property_index("name", "searchable", algorithm=123)  # type: ignore
    weaviate_139_mock.check_assertions()


@pytest.mark.asyncio
async def test_update_property_index_async(
    weaviate_139_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """The async fork of update_property_index submits and waits by polling /indexes.

    Uses unordered handlers because the async client connects inside the test body (its startup
    meta/nodes calls would collide with an ordered sequence); a ready-on-first-poll /indexes still
    exercises the async convergence path.
    """
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="ready", tokenization="field")
    )

    async with weaviate.use_async_with_local(
        host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
    ) as client:
        status = await client.collections.use(COLLECTION).config.update_property_index(
            "name",
            InvertedIndexType.SEARCHABLE,
            tokenization=Tokenization.FIELD,
            wait_for_completion=True,
        )
    assert status.state == InvertedIndexState.READY
    assert status.tokenization == Tokenization.FIELD
    weaviate_139_mock.check_assertions()


@pytest.mark.asyncio
async def test_update_property_index_async_timeout(
    weaviate_139_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """The async wait honors the timeout when the index never reaches ready."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "field"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    weaviate_139_mock.expect_request(INDEXES_PATH, method="GET").respond_with_json(
        _indexes(status="indexing", taskId=TASK_ID, tokenization="word", targetTokenization="field")
    )

    async with weaviate.use_async_with_local(
        host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
    ) as client:
        with pytest.raises(ReindexTimeoutError):
            await client.collections.use(COLLECTION).config.update_property_index(
                "name",
                InvertedIndexType.SEARCHABLE,
                tokenization=Tokenization.FIELD,
                wait_for_completion=True,
                timeout=0.5,
            )
    weaviate_139_mock.check_assertions()


@pytest.mark.asyncio
async def test_rebuild_property_index_async(
    weaviate_139_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """The async fork of rebuild_property_index submits a POST and returns the task."""
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable/rebuild",
        method="POST",
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)

    async with weaviate.use_async_with_local(
        host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
    ) as client:
        task = await client.collections.use(COLLECTION).config.rebuild_property_index(
            "name", InvertedIndexType.SEARCHABLE
        )
    assert task.task_id == TASK_ID
    assert task.status == InvertedIndexTaskStatus.STARTED
    weaviate_139_mock.check_assertions()


def test_property_reindex_unsupported_version(
    weaviate_client: weaviate.WeaviateClient,
) -> None:
    """Every new method raises against a server older than 1.39.0 (the mock advertises 1.36)."""
    config = weaviate_client.collections.use(COLLECTION).config

    with pytest.raises(WeaviateUnsupportedFeatureError):
        config.update_property_index("name", "searchable", tokenization=Tokenization.WORD)
    with pytest.raises(WeaviateUnsupportedFeatureError):
        config.rebuild_property_index("name", "searchable")
    with pytest.raises(WeaviateUnsupportedFeatureError):
        config.cancel_property_index_task("name", "searchable")
    with pytest.raises(WeaviateUnsupportedFeatureError):
        config.get_property_indexes()
