import copy
import json
from typing import Any, Dict, List

import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC


HNSW_CONFIG = {
    "distance": "dot",
    "skip": False,
    "cleanupIntervalSeconds": 300,
    "maxConnections": 64,
    "efConstruction": 128,
    "ef": -1,
    "dynamicEfMin": 100,
    "dynamicEfMax": 500,
    "dynamicEfFactor": 8,
    "vectorCacheMaxObjects": 1000000000000,
    "flatSearchCutoff": 40000,
}
FLAT_CONFIG = {"distance": "dot", "vectorCacheMaxObjects": 1000000000000}
INDEX_CONFIGS = {
    "hnsw": HNSW_CONFIG,
    "flat": FLAT_CONFIG,
    "hfresh": {
        "distance": "dot",
        "maxPostingSizeKB": 48,
        "replicas": 4,
        "searchProbe": 256,
    },
    "dynamic": {
        "distance": "dot",
        "threshold": 10000,
        "hnsw": HNSW_CONFIG,
        "flat": FLAT_CONFIG,
    },
}


@pytest.fixture(params=INDEX_CONFIGS)
def index_type(request: pytest.FixtureRequest) -> str:
    return request.param


@pytest.fixture(params=[False, True], ids=["legacy", "named"])
def named(request: pytest.FixtureRequest) -> bool:
    return request.param


@pytest.fixture
def schema(index_type: str, named: bool) -> Dict[str, Any]:
    index = {
        "vectorIndexType": index_type,
        "vectorIndexConfig": copy.deepcopy(INDEX_CONFIGS[index_type]),
    }
    return {
        "class": "DistanceSource",
        "properties": [],
        "invertedIndexConfig": {
            "bm25": {"b": 0.75, "k1": 1.2},
            "cleanupIntervalSeconds": 60,
            "stopwords": {"preset": "en", "additions": None, "removals": None},
        },
        "replicationConfig": {"factor": 1},
        "shardingConfig": {
            "virtualPerPhysical": 128,
            "desiredCount": 1,
            "actualCount": 1,
            "desiredVirtualCount": 128,
            "actualVirtualCount": 128,
            "key": "_id",
            "strategy": "hash",
            "function": "murmur3",
        },
        **(
            {"vectorConfig": {"custom": {"vectorizer": {"none": {}}, **index}}}
            if named
            else {"vectorizer": "none", **index}
        ),
    }


@pytest.mark.parametrize("from_config", [False, True], ids=["from_dict", "from_config"])
def test_exported_config_preserves_distance_in_create_request(
    weaviate_mock: HTTPServer, schema: Dict[str, Any], named: bool, from_config: bool
) -> None:
    bodies: List[Dict[str, Any]] = []

    def capture_create(request: Request) -> Response:
        body = request.get_json()
        bodies.append(body)
        return Response(json.dumps({"class": body["class"]}), content_type="application/json")

    weaviate_mock.expect_request("/v1/schema/DistanceSource", method="GET").respond_with_json(
        schema
    )
    weaviate_mock.expect_request("/v1/schema", method="POST").respond_with_handler(capture_create)

    with weaviate.connect_to_local(
        port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC, skip_init_checks=True
    ) as client:
        # The unmodified wire schema is a control for the public dictionary creation path.
        client.collections.create_from_dict(schema)
        assert bodies[0] == schema

        config = client.collections.use("DistanceSource").config.get()
        config.name = "DistanceCopy"
        if from_config:
            client.collections.create_from_config(config)
        else:
            client.collections.create_from_dict(config.to_dict())

    weaviate_mock.check_assertions()
    assert len(bodies) == 2
    assert bodies[1]["class"] == "DistanceCopy"
    posted = bodies[1]["vectorConfig"]["custom"] if named else bodies[1]
    index = posted["vectorIndexConfig"]
    assert index.get("distance") == "dot", index
    assert "distanceMetric" not in index
    if posted["vectorIndexType"] == "dynamic":
        for child in ["hnsw", "flat"]:
            assert index[child].get("distance") == "dot", index[child]
            assert "distanceMetric" not in index[child]
