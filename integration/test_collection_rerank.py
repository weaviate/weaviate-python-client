import os

import pytest

import weaviate
import weaviate.classes as wvc
from weaviate.util import _ServerVersion

from .conftest import CollectionFactory


def test_query_using_rerank_with_old_server(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        reranker_config=wvc.Configure.Reranker.transformers(),
        vectorizer_config=wvc.Configure.Vectorizer.none(),
        properties=[wvc.Property(name="text", data_type=wvc.DataType.TEXT)],
        ports=(8079, 50050),
    )

    collection.data.insert_many([{"text": "This is a test"}, {"text": "This is another test"}])

    with pytest.warns(UserWarning):
        objs = collection.query.bm25(
            "test", rerank=wvc.query.Rerank(prop="text", query="another")
        ).objects
        assert len(objs) == 2
        assert objs[0].metadata.rerank_score is None
        assert objs[1].metadata.rerank_score is None


def test_queries_with_rerank() -> None:
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")

    # Make specific client so that we can hard code the correct server version and avoid the BC reranking checks
    client = weaviate.WeaviateClient(
        connection_params=weaviate.ConnectionParams.from_url(
            "http://localhost:8079", grpc_port=50050
        ),
        additional_headers={"X-OpenAI-Api-Key": api_key},
    )
    if client._connection._weaviate_version < _ServerVersion(1, 23, 1):
        pytest.skip("Reranking requires Weaviate 1.23.1 or higher")

    client.collections.delete("Test_test_queries_with_rerank")
    collection = client.collections.create(
        name="Test_test_queries_with_rerank",
        reranker_config=wvc.Configure.Reranker.transformers(),
        vectorizer_config=wvc.Configure.Vectorizer.text2vec_openai(),
        properties=[wvc.Property(name="text", data_type=wvc.DataType.TEXT)],
    )

    insert = collection.data.insert_many(
        [{"text": "This is a test"}, {"text": "This is another test"}]
    )
    uuid1 = insert.uuids[0]
    vector1 = collection.query.fetch_object_by_id(uuid1, include_vector=True).vector
    assert vector1 is not None

    for _idx, query in enumerate(
        [
            lambda: collection.query.bm25(
                "test", rerank=wvc.query.Rerank(prop="text", query="another")
            ),
            lambda: collection.query.hybrid(
                "test", rerank=wvc.query.Rerank(prop="text", query="another")
            ),
            lambda: collection.query.near_object(
                uuid1, rerank=wvc.query.Rerank(prop="text", query="another")
            ),
            lambda: collection.query.near_vector(
                vector1, rerank=wvc.query.Rerank(prop="text", query="another")
            ),
            lambda: collection.query.near_text(
                "test", rerank=wvc.query.Rerank(prop="text", query="another")
            ),
        ]
    ):
        objects = query().objects
        assert len(objects) == 2
        assert objects[0].metadata.rerank_score is not None
        assert objects[1].metadata.rerank_score is not None

        assert [obj for obj in objects if "another" in obj.properties["text"]][  # type: ignore
            0
        ].metadata.rerank_score > [
            obj for obj in objects if "another" not in obj.properties["text"]  # type: ignore
        ][
            0
        ].metadata.rerank_score


def test_queries_with_rerank_and_group_by(collection_factory: CollectionFactory) -> None:
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")

    # Make specific client so that we can hard code the correct server version and avoid the BC reranking checks
    client = weaviate.WeaviateClient(
        connection_params=weaviate.ConnectionParams.from_url(
            "http://localhost:8079", grpc_port=50050
        ),
        additional_headers={"X-OpenAI-Api-Key": api_key},
        skip_init_checks=True,
    )
    # if client._connection._weaviate_version < _ServerVersion(1, 23, 1):
    #     pytest.skip("GroupBy reranking requires Weaviate 1.23.1 or higher")
    client._connection._weaviate_version = _ServerVersion(1, 23, 1)

    client.collections.delete("Test_test_queries_with_rerank_and_group_by")
    collection = client.collections.create(
        name="Test_test_queries_with_rerank_and_group_by",
        reranker_config=wvc.Configure.Reranker.transformers(),
        vectorizer_config=wvc.Configure.Vectorizer.text2vec_openai(vectorize_collection_name=False),
        properties=[wvc.Property(name="text", data_type=wvc.DataType.TEXT)],
    )

    insert = collection.data.insert_many(
        [{"text": "This is a test"}, {"text": "This is another test"}]
    )
    uuid1 = insert.uuids[0]
    vector1 = collection.query.fetch_object_by_id(uuid1, include_vector=True).vector
    assert vector1 is not None

    for _idx, query in enumerate(
        [
            lambda: collection.query.near_object(
                uuid1,
                rerank=wvc.query.Rerank(prop="text", query="another"),
                group_by=wvc.query.GroupBy(prop="text", objects_per_group=1, number_of_groups=2),
            ),
            lambda: collection.query.near_vector(
                vector1,
                rerank=wvc.query.Rerank(prop="text", query="another"),
                group_by=wvc.query.GroupBy(prop="text", objects_per_group=1, number_of_groups=2),
            ),
            lambda: collection.query.near_text(
                "test",
                rerank=wvc.query.Rerank(prop="text", query="another"),
                group_by=wvc.query.GroupBy(prop="text", objects_per_group=1, number_of_groups=2),
            ),
        ]
    ):
        ret = query()
        assert len(ret.groups) == 2
        assert len(ret.objects) == 2
        assert len(list(ret.groups.values())[0].objects) == 1
        assert len(list(ret.groups.values())[1].objects) == 1
        assert ret.objects[0].belongs_to_group is not None
        assert ret.objects[1].belongs_to_group is not None

        assert [group for prop, group in ret.groups.items() if "another" in prop][  # type: ignore
            0
        ].rerank_score > [group for prop, group in ret.groups.items() if "another" not in prop][
            0
        ].rerank_score
