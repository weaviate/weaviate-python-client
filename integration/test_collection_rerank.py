import os

import pytest

import weaviate.classes as wvc

from .conftest import CollectionFactory


def test_queries_with_rerank(collection_factory: CollectionFactory) -> None:
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")

    collection = collection_factory(
        reranker_config=wvc.Configure.Reranker.transformers(),
        vectorizer_config=wvc.Configure.Vectorizer.text2vec_openai(),
        properties=[wvc.Property(name="text", data_type=wvc.DataType.TEXT)],
        ports=(8079, 50050),
        headers={"X-OpenAI-Api-Key": api_key},
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
            obj for obj in objects if "another" not in obj.properties["text"]
        ][
            0
        ].metadata.rerank_score


def test_queries_with_rerank_and_generative(collection_factory: CollectionFactory) -> None:
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")

    collection = collection_factory(
        generative_config=wvc.Configure.Generative.openai(),
        reranker_config=wvc.Configure.Reranker.transformers(),
        vectorizer_config=wvc.Configure.Vectorizer.text2vec_openai(),
        properties=[wvc.Property(name="text", data_type=wvc.DataType.TEXT)],
        ports=(8079, 50050),
        headers={"X-OpenAI-Api-Key": api_key},
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
            obj for obj in objects if "another" not in obj.properties["text"]
        ][
            0
        ].metadata.rerank_score
