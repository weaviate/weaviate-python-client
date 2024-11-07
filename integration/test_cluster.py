from contextlib import contextmanager
from typing import Generator, List

import weaviate
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
)


COLLECTION_NAME_PREFIX = "Collection_test_cluster"
NODE_NAME = "node1"
NUM_OBJECT = 10


@contextmanager
def get_weaviate_client(
    collection_names: List[str],
) -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local()
    for collection_name in collection_names:
        client.collections.delete(collection_name)
    yield client
    for collection_name in collection_names:
        client.collections.delete(collection_name)
    client.close()


def test_rest_nodes_without_data() -> None:
    """get nodes status without data"""
    with get_weaviate_client([]) as client:
        resp = client.cluster.rest_nodes(output="verbose")
        assert len(resp) == 1
        assert "gitHash" in resp[0]
        assert resp[0]["name"] == NODE_NAME
        assert resp[0]["shards"] is None
        assert resp[0]["stats"]["objectCount"] == 0
        assert resp[0]["stats"]["shardCount"] == 0
        assert resp[0]["status"] == "HEALTHY"
        assert "version" in resp[0]


def test_rest_nodes_with_data() -> None:
    """get nodes status with data"""
    collection_name_1 = f"{COLLECTION_NAME_PREFIX}_rest_nodes_with_data_1"
    collection_name_2 = f"{COLLECTION_NAME_PREFIX}_rest_nodes_with_data_2"
    uncap_collection_name_1 = collection_name_1[0].lower() + collection_name_1[1:]

    with get_weaviate_client([collection_name_1, collection_name_2]) as client:
        collection = client.collections.create(
            name=collection_name_1,
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer_config=Configure.Vectorizer.none(),
        )
        collection.data.insert_many([{"Name": f"name {i}"} for i in range(NUM_OBJECT)])

        collection = client.collections.create(
            name=collection_name_2,
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer_config=Configure.Vectorizer.none(),
        )
        collection.data.insert_many([{"Name": f"name {i}"} for i in range(NUM_OBJECT * 2)])

        # server behaviour changed by https://github.com/weaviate/weaviate/pull/4203
        server_is_at_least_124 = client._connection._weaviate_version.is_at_least(1, 24, 0)

        resp = client.cluster.rest_nodes(output="verbose")
        assert len(resp) == 1
        assert "gitHash" in resp[0]
        assert resp[0]["name"] == NODE_NAME
        assert resp[0]["shards"] is not None and len(resp[0]["shards"]) == 2
        assert resp[0]["stats"]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT * 3
        assert resp[0]["stats"]["shardCount"] == 2
        assert resp[0]["status"] == "HEALTHY"
        assert "version" in resp[0]

        shards = sorted(resp[0]["shards"], key=lambda x: x["class"])
        assert shards[0]["class"] == collection_name_1
        assert shards[0]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT
        assert shards[1]["class"] == collection_name_2
        assert shards[1]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT * 2

        resp = client.cluster.rest_nodes(collection=collection_name_1, output="verbose")
        assert len(resp) == 1
        assert "gitHash" in resp[0]
        assert resp[0]["name"] == NODE_NAME
        assert resp[0]["shards"] is not None and len(resp[0]["shards"]) == 1
        assert resp[0]["stats"]["shardCount"] == 1
        assert resp[0]["status"] == "HEALTHY"
        assert "version" in resp[0]
        assert resp[0]["stats"]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT

        resp = client.cluster.rest_nodes(uncap_collection_name_1, output="verbose")
        assert len(resp) == 1
        assert "gitHash" in resp[0]
        assert resp[0]["name"] == NODE_NAME
        assert resp[0]["shards"] is not None and len(resp[0]["shards"]) == 1
        assert resp[0]["stats"]["shardCount"] == 1
        assert resp[0]["status"] == "HEALTHY"
        assert "version" in resp[0]
        assert resp[0]["stats"]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT
