import os

import pytest

import weaviate
import weaviate.classes as wvc


def test_queries_with_rerank() -> None:
    client = weaviate.connect_to_local(port=8084, grpc_port=50055)
    client.collections.delete("TestQueriesWithRerank")
    collection = client.collections.create(
        name="TestQueriesWithRerank",
        reranker_config=wvc.Configure.Reranker.transformers(),
        vectorizer_config=wvc.Configure.Vectorizer.text2vec_transformers(),
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
            lambda: collection.query.bm25("test", rerank=wvc.Rerank(prop="text", query="another")),
            lambda: collection.query.hybrid(
                "test", rerank=wvc.Rerank(prop="text", query="another")
            ),
            lambda: collection.query.near_object(
                uuid1, rerank=wvc.Rerank(prop="text", query="another")
            ),
            lambda: collection.query.near_vector(
                vector1, rerank=wvc.Rerank(prop="text", query="another")
            ),
            lambda: collection.query.near_text(
                "test", rerank=wvc.Rerank(prop="text", query="another")
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


def test_queries_with_rerank_and_generative() -> None:
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")
    client = weaviate.connect_to_local(
        port=8084, grpc_port=50055, headers={"X-OpenAI-Api-Key": api_key}
    )
    client.collections.delete("TestQueriesWithRerankAndGenerative")
    collection = client.collections.create(
        name="TestQueriesWithRerankAndGenerative",
        generative_config=wvc.Configure.Generative.openai(),
        reranker_config=wvc.Configure.Reranker.transformers(),
        vectorizer_config=wvc.Configure.Vectorizer.text2vec_transformers(),
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
                rerank=wvc.Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
            ),
            lambda: collection.generate.hybrid(
                "test",
                rerank=wvc.Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
                grouped_properties=["text"],
                grouped_task="What's going on?",
            ),
            lambda: collection.generate.near_object(
                uuid1,
                rerank=wvc.Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
            ),
            lambda: collection.generate.near_vector(
                vector1,
                rerank=wvc.Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
            ),
            lambda: collection.generate.near_text(
                "test",
                rerank=wvc.Rerank(prop="text", query="another"),
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
