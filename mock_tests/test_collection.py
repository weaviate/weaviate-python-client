from datetime import datetime
import json
import time
from typing import Any, Dict
import grpc
from werkzeug import Request, Response

import pytest
from pytest_httpserver import HTTPServer

import weaviate
from mock_tests.conftest import MOCK_SERVER_URL, MOCK_PORT, MOCK_IP, MOCK_PORT_GRPC, CLIENT_ID
from weaviate.collections.classes.config import (
    CollectionConfig,
    VectorIndexConfigFlat,
    VectorDistances,
    InvertedIndexConfig,
    MultiTenancyConfig,
    BM25Config,
    StopwordsConfig,
    StopwordsPreset,
    ReplicationConfig,
    Vectorizers,
    VectorIndexType,
    ShardingConfig,
)

from weaviate.exceptions import UnexpectedStatusCodeError, WeaviateStartUpError
import weaviate.classes as wvc

from weaviate.connect.base import ConnectionParams, ProtocolParams


ACCESS_TOKEN = "HELLO!IamAnAccessToken"
REFRESH_TOKEN = "UseMeToRefreshYourAccessToken"


@pytest.mark.skip(reason="Fails with gRPC not enabled error")
def test_warning_old_weaviate(recwarn: pytest.WarningsRecorder, ready_mock: HTTPServer) -> None:
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": "1.21.0"})
    ready_mock.expect_request("/v1/objects").respond_with_json({})

    client = weaviate.WeaviateClient(MOCK_SERVER_URL)
    client.collections.get("Class").data.insert(
        {
            "date": datetime.now(),
        }
    )

    assert len(recwarn) == 1
    w = recwarn.pop()
    assert issubclass(w.category, UserWarning)
    assert str(w.message).startswith("Con002")


def test_status_code_exception(weaviate_mock: HTTPServer, start_grpc_server: grpc.Server) -> None:
    weaviate_mock.expect_request("/v1/schema/Test").respond_with_json(response_json={}, status=403)

    client = weaviate.connect_to_local(
        port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC, skip_init_checks=True
    )
    collection = client.collections.get("Test")
    with pytest.raises(UnexpectedStatusCodeError) as e:
        collection.config.get()
    assert e.value.status_code == 403
    weaviate_mock.check_assertions()


def test_old_version(ready_mock: HTTPServer, start_grpc_server: grpc.Server) -> None:
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": "1.23.4"})
    with pytest.raises(WeaviateStartUpError):
        weaviate.connect_to_local(port=MOCK_PORT, host=MOCK_IP, skip_init_checks=True)
    ready_mock.check_assertions()


@pytest.mark.parametrize("header_name", ["Authorization", "authorization"])
def test_auth_header_priority(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server, header_name: str
) -> None:
    """Test that auth_client_secret has priority over the auth header."""

    bearer_token = "OTHER TOKEN"

    weaviate_auth_mock.expect_request("/auth").respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 500, "refresh_token": REFRESH_TOKEN}
    )

    def handler(request: Request) -> Response:
        assert request.headers["Authorization"] == "Bearer " + ACCESS_TOKEN
        return Response(json.dumps({}))

    weaviate_auth_mock.expect_request("/v1/schema").respond_with_handler(handler)

    with pytest.warns(UserWarning) as recwarn:
        weaviate.connect_to_local(
            port=MOCK_PORT,
            host=MOCK_IP,
            grpc_port=MOCK_PORT_GRPC,
            headers={header_name: "Bearer " + bearer_token},
            auth_credentials=wvc.init.Auth.api_key("key"),
        )
        assert str(recwarn[0].message).startswith("Auth004")


def test_auth_header_with_catchall_proxy(
    weaviate_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """Test that the client can handle situations in which a proxy returns a catchall page for all requests."""
    weaviate_mock.expect_request("/v1/schema").respond_with_json({})
    weaviate_mock.expect_request("/v1/.well-known/openid-configuration").respond_with_data(
        "JsonCannotParseThis"
    )

    with pytest.warns(UserWarning) as recwarn:
        weaviate.connect_to_local(
            port=MOCK_PORT,
            grpc_port=MOCK_PORT_GRPC,
            host=MOCK_IP,
            auth_credentials=wvc.init.Auth.bearer_token("token"),
        )
        assert str(recwarn[0].message).startswith("Auth005")


def test_refresh(weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server) -> None:
    """Test that refresh tokens are used to get a new access token."""
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": {}})

    weaviate_auth_mock.expect_request(
        "/auth",
        data=f"grant_type=refresh_token&refresh_token={REFRESH_TOKEN}&client_id={CLIENT_ID}",
    ).respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 1, "refresh_token": REFRESH_TOKEN}
    )
    with weaviate.connect_to_local(
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        host=MOCK_IP,
        auth_credentials=wvc.init.Auth.bearer_token(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=1
        ),
    ) as client:
        time.sleep(1)  # client gets a new token 1s before expiration
        client.collections.list_all()


def test_closed_connection(weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server) -> None:
    client = weaviate.WeaviateClient(
        ConnectionParams(
            grpc=ProtocolParams(host=MOCK_IP, port=MOCK_PORT_GRPC, secure=False),
            http=ProtocolParams(host=MOCK_IP, port=MOCK_PORT, secure=False),
        )
    )
    with pytest.raises(weaviate.exceptions.WeaviateClosedClientError):
        client.collections.list_all()
    with pytest.raises(weaviate.exceptions.WeaviateClosedClientError):
        collection = client.collections.get("Test")
        collection.query.fetch_objects()
    with pytest.raises(weaviate.exceptions.WeaviateClosedClientError):
        collection = client.collections.get("Test")
        collection.data.insert_many([{}])


def test_missing_multi_tenancy_config(
    weaviate_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    vic = VectorIndexConfigFlat(
        quantizer=None,
        distance_metric=VectorDistances.COSINE,
        vector_cache_max_objects=10,
    )
    vic.distance = vic.distance_metric
    response_json = CollectionConfig(
        name="Test",
        description="",
        generative_config=None,
        reranker_config=None,
        vectorizer_config=None,
        vector_config=None,
        inverted_index_config=InvertedIndexConfig(
            bm25=BM25Config(b=0, k1=0),
            cleanup_interval_seconds=0,
            index_null_state=False,
            index_property_length=False,
            index_timestamps=False,
            stopwords=StopwordsConfig(preset=StopwordsPreset.NONE, additions=[], removals=[]),
        ),
        multi_tenancy_config=MultiTenancyConfig(enabled=True),
        sharding_config=ShardingConfig(
            virtual_per_physical=0,
            desired_count=0,
            actual_count=0,
            desired_virtual_count=0,
            actual_virtual_count=0,
            key="",
            strategy="",
            function="",
        ),
        properties=[],
        references=[],
        replication_config=ReplicationConfig(factor=0),
        vector_index_config=vic,
        vector_index_type=VectorIndexType.FLAT,
        vectorizer=Vectorizers.NONE,
    ).to_dict()

    weaviate_mock.expect_request("/v1/schema/TestTrue").respond_with_json(
        response_json=response_json, status=200
    )
    client = weaviate.connect_to_local(
        port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC, skip_init_checks=True
    )
    collection = client.collections.get("TestTrue")
    conf = collection.config.get()
    assert conf.multi_tenancy_config.enabled is True

    # Delete the missing configuration for multy tenancy
    response_json["name"] = "TestFalse"
    del response_json["multiTenancyConfig"]
    weaviate_mock.expect_request("/v1/schema/TestFalse").respond_with_json(
        response_json=response_json, status=200
    )
    client = weaviate.connect_to_local(
        port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC, skip_init_checks=True
    )
    collection = client.collections.get("TestFalse")

    conf = collection.config.get()
    assert conf.multi_tenancy_config.enabled is False


def test_return_from_bind_module(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    config = wvc.config.Configure

    # point of this test is to check if the return from the bind module is correctly parsed. There is no skip and vectorizePropertyName present
    prop_modconf: Dict[str, Any] = {"multi2vec-bind": {}}

    hnsw_config = config.VectorIndex.hnsw(
        1, VectorDistances.COSINE, 1, 1, 1, 1, 1, 1, 1, 1
    )._to_dict()
    hnsw_config["skip"] = True
    ii_config = config.inverted_index(
        1, 1, 1, True, True, True, StopwordsPreset.EN, [], []
    )._to_dict()
    schema = {
        "class": "TestBindCollection",
        "properties": [
            {
                "dataType": ["text"],
                "name": "name",
                "indexFilterable": False,
                "indexSearchable": False,
                "moduleConfig": prop_modconf,
            },
        ],
        "vectorIndexConfig": hnsw_config,
        "vectorIndexType": "hnsw",
        "invertedIndexConfig": ii_config,
        "multiTenancyConfig": config.multi_tenancy()._to_dict(),
        "vectorizer": "multi2vec-bind",
        "replicationConfig": {"factor": 2},
        "moduleConfig": {"multi2vec-bind": {}},
    }
    weaviate_auth_mock.expect_request("/v1/schema/TestBindCollection").respond_with_json(
        response_json=schema, status=200
    )
    client = weaviate.connect_to_local(
        port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC, skip_init_checks=True
    )
    collection = client.collections.get("TestBindCollection")
    conf = collection.config.get()

    assert conf.properties[0].vectorizer_config is not None
    assert not conf.properties[0].vectorizer_config.skip
    assert not conf.properties[0].vectorizer_config.vectorize_property_name
