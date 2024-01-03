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


def test_queries_with_rerank_and_generative(collection_factory: CollectionFactory) -> None:
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
        pytest.skip("Generative reranking requires Weaviate 1.23.1 or higher")

    collection = client.collections.create(
        name="Test_test_queries_with_rerank_and_generative",
        generative_config=wvc.Configure.Generative.openai(),
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
            lambda: collection.generate.bm25(
                "test",
                rerank=wvc.query.Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
            ),
            lambda: collection.generate.hybrid(
                "test",
                rerank=wvc.query.Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
                grouped_properties=["text"],
                grouped_task="What's going on?",
            ),
            lambda: collection.generate.near_object(
                uuid1,
                rerank=wvc.query.Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
            ),
            lambda: collection.generate.near_vector(
                vector1,
                rerank=wvc.query.Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
            ),
            lambda: collection.generate.near_text(
                "test",
                rerank=wvc.query.Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
            ),
        ]
    ):
        objects = query().objects
        assert len(objects) == 2
        assert objects[0].metadata.rerank_score is not None
        assert objects[0].generated is not None
        assert objects[1].metadata.rerank_score is not None
        assert objects[1].generated is not None

        assert [obj for obj in objects if "another" in obj.properties["text"]][  # type: ignore
            0
        ].metadata.rerank_score > [
            obj for obj in objects if "another" not in obj.properties["text"]  # type: ignore
        ][
            0
        ].metadata.rerank_score
