import json
from typing import Generator

import grpc
import pytest
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC
from weaviate.collections.classes.config import (
    PropertyIndexState,
    PropertyIndexTaskStatus,
    Tokenization,
)
from weaviate.exceptions import (
    ReindexCanceledError,
    ReindexFailedError,
    WeaviateUnsupportedFeatureError,
)

COLLECTION = "TestCollection"
SCHEMA_PATH = f"/v1/schema/{COLLECTION}"
TASK_ID = "00000000-0000-0000-0000-000000000001"


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
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "word", "algorithm": "blockmax"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)

    task = client_139.collections.use(COLLECTION).config.update_property_index(
        "name",
        "searchable",
        tokenization=Tokenization.WORD,
        algorithm="blockmax",
    )
    assert task.task_id == TASK_ID
    assert task.status == PropertyIndexTaskStatus.STARTED
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
    assert task.status == PropertyIndexTaskStatus.NO_OP
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
    assert task.status == PropertyIndexTaskStatus.STARTED
    weaviate_139_mock.check_assertions()


def test_update_property_index_wait_for_completion(
    weaviate_139_mock: HTTPServer, client_139: weaviate.WeaviateClient
) -> None:
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "word"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
    weaviate_139_mock.expect_request(f"{SCHEMA_PATH}/indexes", method="GET").respond_with_json(
        {
            "collection": COLLECTION,
            "properties": [
                {
                    "name": "name",
                    "dataType": "text",
                    "indexes": [{"type": "searchable", "status": "ready", "tokenization": "word"}],
                }
            ],
        }
    )

    status = client_139.collections.use(COLLECTION).config.update_property_index(
        "name", "searchable", tokenization=Tokenization.WORD, wait_for_completion=True
    )
    assert status.type == "searchable"
    assert status.status == PropertyIndexState.READY
    assert status.tokenization == Tokenization.WORD
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
    assert task.status == PropertyIndexTaskStatus.STARTED
    weaviate_139_mock.check_assertions()


@pytest.mark.parametrize(
    "index_status,exception",
    [("failed", ReindexFailedError), ("cancelled", ReindexCanceledError)],
)
def test_update_property_index_wait_raises(
    weaviate_139_mock: HTTPServer,
    client_139: weaviate.WeaviateClient,
    index_status: str,
    exception: type,
) -> None:
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable",
        method="PUT",
        json={"tokenization": "word"},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
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
                            "status": index_status,
                            "progress": 0.42,
                            "taskId": TASK_ID,
                            "tokenization": "word",
                        }
                    ],
                }
            ],
        }
    )

    with pytest.raises(exception):
        client_139.collections.use(COLLECTION).config.update_property_index(
            "name", "searchable", tokenization=Tokenization.WORD, wait_for_completion=True
        )
    weaviate_139_mock.check_assertions()


@pytest.mark.parametrize(
    "index_status,exception",
    [("failed", ReindexFailedError), ("cancelled", ReindexCanceledError)],
)
def test_rebuild_property_index_wait_raises(
    weaviate_139_mock: HTTPServer,
    client_139: weaviate.WeaviateClient,
    index_status: str,
    exception: type,
) -> None:
    weaviate_139_mock.expect_request(
        f"{SCHEMA_PATH}/properties/name/index/searchable/rebuild",
        method="POST",
        json={},
    ).respond_with_json({"taskId": TASK_ID, "status": "STARTED"}, status=202)
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
                            "status": index_status,
                            "progress": 0.42,
                            "taskId": TASK_ID,
                            "tokenization": "word",
                        }
                    ],
                }
            ],
        }
    )

    with pytest.raises(exception):
        client_139.collections.use(COLLECTION).config.rebuild_property_index(
            "name", "searchable", wait_for_completion=True
        )
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
    assert task.status == PropertyIndexTaskStatus.STARTED
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
    assert task.status == PropertyIndexTaskStatus.STARTED
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
    assert task.status == PropertyIndexTaskStatus.CANCELLED
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
    assert task.status == PropertyIndexTaskStatus.NO_OP
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
    assert searchable.type == "searchable"
    assert searchable.status == PropertyIndexState.INDEXING
    assert searchable.progress == 0.5
    assert searchable.task_id == TASK_ID
    assert searchable.tokenization == Tokenization.WORD
    assert searchable.target_tokenization == Tokenization.FIELD
    assert searchable.algorithm == "wand"
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
    assert age.indexes[0].status == PropertyIndexState.READY
    assert age.indexes[0].progress is None
    assert age.indexes[0].task_id is None
    assert age.indexes[0].tokenization is None

    # the nested dataclasses serialize all the way down to a JSON-compatible dict
    out = json.loads(json.dumps(indexes.to_dict()))
    assert out["collection"] == COLLECTION
    assert out["properties"][0]["indexes"][0]["taskId"] == TASK_ID
    assert out["properties"][0]["indexes"][0]["targetTokenization"] == "field"
    assert out["properties"][1]["dataType"] == "int"
    assert out["properties"][1]["indexes"][0]["status"] == "ready"

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
