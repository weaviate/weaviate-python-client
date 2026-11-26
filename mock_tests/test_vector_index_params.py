"""``vector_index_params`` reaches the wire through the public collection API.

The unit tests in ``test/collection/test_vector_index_params.py`` cover the request builder;
these go through ``collection.query`` / ``collection.generate`` against a gRPC server stub that
records the ``SearchRequest`` it receives.
"""

from typing import Callable, Generator, List, Tuple

import grpc
import pytest
from pytest_httpserver import HTTPServer

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC
from weaviate.classes.config import VectorFilterStrategy
from weaviate.classes.query import HybridVector, NearMediaType, VectorIndexParams
from weaviate.collections.classes.grpc import VectorIndexParamsReturn
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
    return weaviate_client_1_42.collections.use("VectorIndexParamsCollection"), service


def test_query_near_vector_sends_ef(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.query.near_vector([1.0, 0.0], vector_index_params=VectorIndexParams.hnsw(ef=128))

    (req,) = service.requests
    assert req.HasField("vector_index_params")
    assert req.vector_index_params.ef == 128


def test_query_near_vector_default_sends_nothing(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.query.near_vector([1.0, 0.0])

    (req,) = service.requests
    assert not req.HasField("vector_index_params")


def test_query_hybrid_sends_ef(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.query.hybrid(
        "cats",
        vector=HybridVector.near_vector([1.0, 0.0]),
        vector_index_params=VectorIndexParams.hnsw(ef=32),
    )

    (req,) = service.requests
    assert req.HasField("hybrid_search")
    assert req.vector_index_params.ef == 32


def test_generate_near_object_sends_ef(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.generate.near_object(
        "00000000-0000-0000-0000-000000000001",
        single_prompt="Say hi to {name}",
        vector_index_params=VectorIndexParams.hnsw(ef=16),
    )

    (req,) = service.requests
    assert req.HasField("generative")
    assert req.vector_index_params.ef == 16


def test_query_near_vector_sends_every_hnsw_knob(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.query.near_vector(
        [1.0, 0.0],
        vector_index_params=VectorIndexParams.hnsw(
            ef=64, filter_strategy=VectorFilterStrategy.ACORN
        ),
    )

    (req,) = service.requests
    assert req.vector_index_params.ef == 64
    assert not req.vector_index_params.HasField("search_probe")
    assert req.vector_index_params.filter_strategy == search_get_pb2.FILTER_STRATEGY_ACORN
    assert len(req.vector_index_params_for_targets) == 0


def test_query_near_vector_mapping_sends_per_target_entries(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
) -> None:
    collection, service = capture_collection
    collection.query.near_vector(
        [1.0, 0.0],
        target_vector=["title", "body"],
        vector_index_params={
            "title": VectorIndexParams.hnsw(ef=16, filter_strategy=VectorFilterStrategy.PATHSEER),
            "body": VectorIndexParams.hfresh(search_probe=4),
        },
    )

    (req,) = service.requests
    assert not req.HasField("vector_index_params")
    by_target = {e.target: e.params for e in req.vector_index_params_for_targets}
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
        vector_index_params={"title": VectorIndexParams.hnsw(ef=24)},
    )

    (req,) = service.requests
    assert req.HasField("generative")
    assert req.HasField("hybrid_search")
    (entry,) = req.vector_index_params_for_targets
    assert entry.target == "title"
    assert entry.params.ef == 24


_UUID = "00000000-0000-0000-0000-000000000001"
_PROMPT = "Say hi to {name}"

# Every public entry point that accepts the option, so a dropped kwarg in one executor forward
# cannot pass unnoticed.
_ENTRY_POINTS: dict[
    str, Callable[[weaviate.collections.Collection, VectorIndexParamsReturn], object]
] = {
    "query.near_vector": lambda c, p: c.query.near_vector([1.0, 0.0], vector_index_params=p),
    "query.near_object": lambda c, p: c.query.near_object(_UUID, vector_index_params=p),
    "query.near_text": lambda c, p: c.query.near_text("cats", vector_index_params=p),
    "query.near_image": lambda c, p: c.query.near_image("YWJj", vector_index_params=p),
    "query.near_media": lambda c, p: c.query.near_media(
        "YWJj", NearMediaType.IMAGE, vector_index_params=p
    ),
    "query.hybrid": lambda c, p: c.query.hybrid(
        "cats", vector=HybridVector.near_vector([1.0, 0.0]), vector_index_params=p
    ),
    "generate.near_vector": lambda c, p: c.generate.near_vector(
        [1.0, 0.0], single_prompt=_PROMPT, vector_index_params=p
    ),
    "generate.near_object": lambda c, p: c.generate.near_object(
        _UUID, single_prompt=_PROMPT, vector_index_params=p
    ),
    "generate.near_text": lambda c, p: c.generate.near_text(
        "cats", single_prompt=_PROMPT, vector_index_params=p
    ),
    "generate.near_image": lambda c, p: c.generate.near_image(
        "YWJj", single_prompt=_PROMPT, vector_index_params=p
    ),
    "generate.near_media": lambda c, p: c.generate.near_media(
        "YWJj", NearMediaType.IMAGE, single_prompt=_PROMPT, vector_index_params=p
    ),
    "generate.hybrid": lambda c, p: c.generate.hybrid(
        "cats",
        vector=HybridVector.near_vector([1.0, 0.0]),
        single_prompt=_PROMPT,
        vector_index_params=p,
    ),
}


@pytest.mark.parametrize("entry_point", list(_ENTRY_POINTS), ids=list(_ENTRY_POINTS))
def test_every_entry_point_forwards_the_option(
    capture_collection: Tuple[weaviate.collections.Collection, _SearchRequestCapture],
    entry_point: str,
) -> None:
    collection, service = capture_collection
    _ENTRY_POINTS[entry_point](collection, VectorIndexParams.hnsw(ef=48))

    (req,) = service.requests
    assert req.HasField("vector_index_params"), entry_point
    assert req.vector_index_params.ef == 48


def test_old_server_rejected_before_any_request(
    weaviate_client: weaviate.WeaviateClient, start_grpc_server: grpc.Server
) -> None:
    # conftest's weaviate_client talks to a mock reporting Weaviate 1.36.
    service = _SearchRequestCapture()
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(service, start_grpc_server)
    collection = weaviate_client.collections.use("VectorIndexParamsCollection")

    with pytest.raises(WeaviateUnsupportedFeatureError):
        collection.query.near_vector([1.0, 0.0], vector_index_params=VectorIndexParams.hnsw(ef=128))
    assert service.requests == []

    # Without the option the same client still searches.
    collection.query.near_vector([1.0, 0.0])
    assert len(service.requests) == 1
