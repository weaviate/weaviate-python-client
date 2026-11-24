"""``vector_search_params`` reaches the wire through the public collection API.

The unit tests in ``test/collection/test_vector_search_params.py`` cover the request builder;
these go through ``collection.query`` / ``collection.generate`` against a gRPC server stub that
records the ``SearchRequest`` it receives.
"""

from typing import Generator, List, Tuple

import grpc
import pytest
from pytest_httpserver import HTTPServer

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC
from weaviate.classes.query import HybridVector, VectorSearchParams
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.proto.v1 import search_get_pb2, weaviate_pb2_grpc


class _SearchRequestCapture(weaviate_pb2_grpc.WeaviateServicer):
    def __init__(self) -> None:
        self.requests: List[search_get_pb2.SearchRequest] = []

    def Search(
        self, request: search_get_pb2.SearchRequest, context: grpc.ServicerContext
    ) -> search_get_pb2.SearchReply:
        self.requests.append(request)
        return search_get_pb2.SearchReply()


@pytest.fixture(scope="function")
def weaviate_client_1_42(
    ready_mock: HTTPServer, start_grpc_server: grpc.Server
) -> Generator[weaviate.WeaviateClient, None, None]:
    # Same as conftest's weaviate_client, but the shared mock reports 1.36 and the option is gated on 1.42.
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": "1.42.0"})
    ready_mock.expect_request("/v1/nodes").respond_with_json(
        {"nodes": [{"gitHash": "ABC", "status": "HEALTHY"}]}
    )
    client = weaviate.connect_to_local(port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC)
    yield client
    client.close()


@pytest.fixture(scope="function")
def capture_collection(
    weaviate_client_1_42: weaviate.WeaviateClient, start_grpc_server: grpc.Server
) -> Tuple[weaviate.collections.Collection, _SearchRequestCapture]:
    service = _SearchRequestCapture()
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(service, start_grpc_server)
    return weaviate_client_1_42.collections.use("VectorSearchParamsCollection"), service


def test_query_near_vector_sends_ef(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.query.near_vector([1.0, 0.0], vector_search_params=VectorSearchParams(ef=128))

    (req,) = service.requests
    assert req.HasField("vector_search_params")
    assert req.vector_search_params.ef == 128


def test_query_near_vector_default_sends_nothing(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.query.near_vector([1.0, 0.0])

    (req,) = service.requests
    assert not req.HasField("vector_search_params")


def test_query_hybrid_sends_ef(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.query.hybrid(
        "cats",
        vector=HybridVector.near_vector([1.0, 0.0]),
        vector_search_params=VectorSearchParams(ef=32),
    )

    (req,) = service.requests
    assert req.HasField("hybrid_search")
    assert req.vector_search_params.ef == 32


def test_generate_near_object_sends_ef(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.generate.near_object(
        "00000000-0000-0000-0000-000000000001",
        single_prompt="Say hi to {name}",
        vector_search_params=VectorSearchParams(ef=16),
    )

    (req,) = service.requests
    assert req.HasField("generative")
    assert req.vector_search_params.ef == 16


def test_query_near_vector_sends_every_knob(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.query.near_vector(
        [1.0, 0.0],
        vector_search_params=VectorSearchParams(ef=64, search_probe=8, filter_strategy="acorn"),
    )

    (req,) = service.requests
    assert req.vector_search_params.ef == 64
    assert req.vector_search_params.search_probe == 8
    assert req.vector_search_params.filter_strategy == search_get_pb2.FILTER_STRATEGY_ACORN
    assert len(req.vector_search_params_for_targets) == 0


def test_query_near_vector_mapping_sends_per_target_entries(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.query.near_vector(
        [1.0, 0.0],
        target_vector=["title", "body"],
        vector_search_params={
            "title": VectorSearchParams.hnsw(ef=16, filter_strategy="pathseer"),
            "body": VectorSearchParams.hfresh(search_probe=4),
        },
    )

    (req,) = service.requests
    assert not req.HasField("vector_search_params")
    by_target = {e.target: e.params for e in req.vector_search_params_for_targets}
    assert set(by_target) == {"title", "body"}
    assert by_target["title"].ef == 16
    assert by_target["title"].filter_strategy == search_get_pb2.FILTER_STRATEGY_PATHSEER
    assert by_target["body"].search_probe == 4
    assert not by_target["body"].HasField("ef")


def test_generate_hybrid_mapping_sends_per_target_entries(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.generate.hybrid(
        "cats",
        vector=HybridVector.near_vector([1.0, 0.0]),
        target_vector=["title"],
        single_prompt="Say hi to {name}",
        vector_search_params={"title": VectorSearchParams(ef=24)},
    )

    (req,) = service.requests
    assert req.HasField("generative")
    assert req.HasField("hybrid_search")
    (entry,) = req.vector_search_params_for_targets
    assert entry.target == "title"
    assert entry.params.ef == 24


def test_old_server_rejected_before_any_request(
    weaviate_client: weaviate.WeaviateClient, start_grpc_server: grpc.Server
) -> None:
    # conftest's weaviate_client talks to a mock reporting Weaviate 1.36.
    service = _SearchRequestCapture()
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(service, start_grpc_server)
    collection = weaviate_client.collections.use("VectorSearchParamsCollection")

    with pytest.raises(WeaviateUnsupportedFeatureError):
        collection.query.near_vector([1.0, 0.0], vector_search_params=VectorSearchParams(ef=128))
    assert service.requests == []

    # Without the option the same client still searches.
    collection.query.near_vector([1.0, 0.0])
    assert len(service.requests) == 1
