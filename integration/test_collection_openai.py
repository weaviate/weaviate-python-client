import os
from typing import List

import pytest
from _pytest.fixtures import SubRequest

import weaviate
from integration.conftest import CollectionFactory, OpenAICollection
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
)
from weaviate.collections.classes.data import DataObject
from weaviate.collections.classes.grpc import GroupBy, Rerank
from weaviate.exceptions import WeaviateQueryError
from weaviate.util import _ServerVersion


@pytest.mark.parametrize("parameter,answer", [("text", "yes"), ("content", "no")])
def test_generative_search_single(
    openai_collection: OpenAICollection, parameter: str, answer: str
) -> None:
    collection = openai_collection()

    collection.data.insert_many(
        [
            DataObject(properties={"text": "bananas are great", "content": "bananas are bad"}),
            DataObject(properties={"text": "apples are great", "content": "apples are bad"}),
        ]
    )

    res = collection.generate.fetch_objects(
        single_prompt=f"is it good or bad based on {{{parameter}}}? Just answer with yes or no without punctuation",
    )
    for obj in res.objects:
        assert obj.generated is not None
        assert obj.generated.lower() == answer
    assert res.generated is None


@pytest.mark.parametrize(
    "prop,answer", [(["text"], "apples bananas"), (["content"], "bananas apples")]
)
def test_fetch_objects_generate_search_grouped(
    openai_collection: OpenAICollection, prop: List[str], answer: str
) -> None:
    collection = openai_collection()

    collection.data.insert_many(
        [
            DataObject(properties={"text": "apples are big", "content": "apples are small"}),
            DataObject(properties={"text": "bananas are small", "content": "bananas are big"}),
        ]
    )

    res = collection.generate.fetch_objects(
        grouped_task="What is big and what is small? write the name of the big thing first and then the name of the small thing after a space. Dont write anything else",
        grouped_properties=prop,
    )
    assert res.generated == answer


def test_fetch_objects_generate_search_grouped_all_props(
    openai_collection: OpenAICollection, request: SubRequest
) -> None:
    collection = openai_collection()

    collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "apples are big. Apples are smaller than Teddy and bigger than bananas",
                    "content": "Teddy is the biggest and bigger than everything else. Teddy is bigger than apples.",
                }
            ),
            DataObject(
                properties={
                    "text": "bananas are small. Bananas are smaller than apples and bigger than cats",
                    "content": "cats are the smallest and smaller than everything else. Cats are smaller than bananas",
                }
            ),
        ]
    )

    res = collection.generate.fetch_objects(
        grouped_task="What is the biggest and what is the smallest? Only write the names separated by a space. Dont write anything else"
    )
    assert res.generated == "Teddy cats"


def test_fetch_objects_generate_search_grouped_specified_prop(
    openai_collection: OpenAICollection,
) -> None:
    collection = openai_collection()

    collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "apples are big",
                    "content": "Teddy is the biggest and bigger than everything else",
                }
            ),
            DataObject(
                properties={
                    "text": "bananas are small",
                    "content": "cats are the smallest and smaller than everything else",
                }
            ),
        ]
    )

    res = collection.generate.fetch_objects(
        grouped_task="What is the biggest and what is the smallest? Only write the names separated by a space",
        grouped_properties=["text"],
    )
    assert res.generated == "apples bananas"


def test_fetch_objects_generate_with_everything(openai_collection: OpenAICollection) -> None:
    collection = openai_collection()

    collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "apples are big. Apples are smaller than Teddy and bigger than bananas",
                    "content": "Teddy is the biggest and bigger than everything else",
                }
            ),
            DataObject(
                properties={
                    "text": "bananas are small. Bananas are smaller than apples and bigger than cats.",
                    "content": "cats are the smallest and smaller than everything else",
                }
            ),
        ]
    )

    res = collection.generate.fetch_objects(
        single_prompt="Is there something to eat in {text}? Only answer yes if there is something to eat or no if not without punctuation",
        grouped_task="What is the biggest and what is the smallest? Only write the names separated by a space",
    )
    assert res.generated == "Teddy cats"
    for obj in res.objects:
        assert obj.generated == "Yes"


def test_bm25_generate_with_everything(
    openai_collection: OpenAICollection, request: SubRequest
) -> None:
    collection = openai_collection()

    collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "apples are big",
                    "content": "Teddy is the biggest and bigger than everything else",
                }
            ),
            DataObject(
                properties={
                    "text": "bananas are small",
                    "content": "cats are the smallest and smaller than everything else",
                }
            ),
        ]
    )

    res = collection.generate.bm25(
        query="Teddy",
        query_properties=["content"],
        single_prompt="Is there something to eat in {text}? Only answer yes if there is something to eat or no if not without punctuation",
        grouped_task="What is the biggest and what is the smallest? Only write the names separated by a space",
    )
    assert res.generated == "Teddy apples"
    for obj in res.objects:
        assert obj.generated == "Yes"


def test_hybrid_generate_with_everything(
    openai_collection: OpenAICollection, request: SubRequest
) -> None:
    collection = openai_collection()

    collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "apples are big. You can eat apples",
                    "content": "Teddy is the biggest and bigger than everything else",
                }
            ),
            DataObject(
                properties={
                    "text": "cats are small. You cannot eat cats",
                    "content": "bananas are the smallest and smaller than everything else",
                }
            ),
        ]
    )

    res = collection.generate.hybrid(
        query="cats",
        alpha=0,
        query_properties=["text"],
        single_prompt="Does {text} mention cats? Only answer yes if there is the word cat or cats in the text and no if not. Dont use punctuation",
        grouped_task="What is the biggest and what is the smallest? Only write the names separated by a space from biggest to smallest",
    )
    assert res.generated == "cats bananas"
    for obj in res.objects:
        assert obj.generated is not None
        assert obj.generated.lower() == "yes"


def test_near_object_generate_with_everything(openai_collection: OpenAICollection) -> None:
    collection = openai_collection(
        vectorizer_config=Configure.Vectorizer.text2vec_openai(vectorize_collection_name=False),
    )

    ret = collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "apples are big",
                    "content": "Teddy is the biggest and bigger than everything else",
                }
            ),
            DataObject(
                properties={
                    "text": "cats are small. you cannot eat cats.",
                    "content": "bananas are the smallest and smaller than everything else",
                }
            ),
        ]
    )

    res = collection.generate.near_object(
        ret.uuids[1],
        single_prompt="Are cats mentioned in {text} of the given object? Only answer yes if there is the word cat or cats and no if not. Dont use punctuation",
        grouped_task="What is the biggest and what is the smallest? Only write the names separated by a space from biggest to smallest",
        grouped_properties=["text"],
    )
    assert res.generated == "apples cats"
    assert res.objects[0].generated is not None
    assert res.objects[1].generated is not None
    assert res.objects[0].generated.lower() == "yes"
    assert res.objects[1].generated.lower() == "no"


def test_near_object_generate_and_group_by_with_everything(
    openai_collection: OpenAICollection,
) -> None:
    collection = openai_collection(
        vectorizer_config=Configure.Vectorizer.text2vec_openai(vectorize_collection_name=False),
    )

    ret = collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "apples are big. you cna eat apples",
                    "content": "Teddy is the biggest and bigger than everything else",
                }
            ),
            DataObject(
                properties={
                    "text": "cats are small. you cannot eat cats",
                    "content": "bananas are the smallest and smaller than everything else",
                }
            ),
        ]
    )

    res = collection.generate.near_object(
        ret.uuids[1],
        single_prompt="Is there something to eat in {text} in the given object? Only answer yes if there is something to eat or no if not without punctuation",
        grouped_task="What is the biggest and what is the smallest? Only write the names separated by a space from biggest to smallest",
        grouped_properties=["text"],
        group_by=GroupBy(prop="text", number_of_groups=2, objects_per_group=1),
    )
    assert res.generated == "apples cats"
    assert len(res.groups) == 2
    groups = list(res.groups.values())
    assert groups[0].generated is not None
    assert groups[1].generated is not None
    assert groups[0].generated.lower() == "no"
    assert groups[1].generated.lower() == "yes"


def test_near_text_generate_with_everything(openai_collection: OpenAICollection) -> None:
    collection = openai_collection(
        vectorizer_config=Configure.Vectorizer.text2vec_openai(vectorize_collection_name=False),
    )

    collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "melons are big",
                    "content": "Teddy is the biggest and bigger than everything else. Teddy is not a fruit",
                }
            ),
            DataObject(
                properties={
                    "text": "cats are small. You cannot eat cats. Cats are not fruit",
                    "content": "bananas are the smallest and smaller than everything else",
                }
            ),
        ]
    )

    res = collection.generate.near_text(
        query="small fruit",
        single_prompt="Is there something to eat in {text} of the given object? Only answer yes if there is something to eat and no if not. Dont use punctuation",
        grouped_task="Write out the fruit in alphabetical order. Only write the names separated by a space",
    )
    assert res.generated == "bananas melons"
    assert res.objects[0].generated is not None
    assert res.objects[1].generated is not None
    assert res.objects[0].generated.lower() == "no"
    assert res.objects[1].generated.lower() == "yes"


def test_near_text_generate_and_group_by_with_everything(
    openai_collection: OpenAICollection,
) -> None:
    collection = openai_collection(
        vectorizer_config=Configure.Vectorizer.text2vec_openai(vectorize_collection_name=False),
    )

    collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "apples are big",
                    "content": "Teddy is the biggest and bigger than everything else. Teddy is not a fruit",
                },
            ),
            DataObject(
                properties={
                    "text": "cats are small. you cannot eat cats. Cats are not fruit",
                    "content": "bananas are the smallest and smaller than everything else",
                },
            ),
        ]
    )

    res = collection.generate.near_text(
        query="small fruit",
        single_prompt="Is there something to eat in {text} of the given object? Only answer yes if there is something to eat and no if not. Dont use punctuation",
        grouped_task="Write out the fruit in alphabetical order. Only write the names separated by a space",
        group_by=GroupBy(prop="text", number_of_groups=2, objects_per_group=1),
    )
    assert res.generated == "apples bananas"
    assert len(res.groups) == 2
    groups = list(res.groups.values())
    assert groups[0].generated is not None
    assert groups[1].generated is not None
    assert groups[0].generated.lower() == "no"
    assert groups[1].generated.lower() == "yes"


def test_near_vector_generate_with_everything(openai_collection: OpenAICollection) -> None:
    collection = openai_collection()

    collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "apples are big",
                    "content": "Teddy is the biggest and bigger than everything else",
                },
                vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            ),
            DataObject(
                properties={
                    "text": "cats are small. Cats are not fruit. You cannot eat cats",
                    "content": "bananas are the smallest and smaller than everything else",
                },
                vector=[0.6, 0.7, 0.8, 0.9, 0.99],
            ),
        ]
    )

    res = collection.generate.near_vector(
        near_vector=[0.1, 0.2, 0.3, 0.4, 0.6],
        single_prompt="Is there something to eat in {text}? Only answer yes if there is something to eat or no if not without punctuation",
        grouped_task="Write out the fruit in the order in which they appear in the provided list. Only write the names separated by a space",
    )
    assert res.generated == "apples bananas"
    assert res.objects[0].generated == "Yes"
    assert res.objects[1].generated == "No"


def test_near_vector_generate_and_group_by_with_everything(
    openai_collection: OpenAICollection, request: SubRequest
) -> None:
    collection = openai_collection()

    collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "apples are big",
                    "content": "Teddy is the biggest and bigger than everything else",
                },
                vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            ),
            DataObject(
                properties={
                    "text": "cats are small. Cats are not a fruit, you cannot eat cats.",
                    "content": "bananas are the smallest and smaller than everything else",
                },
                vector=[0.6, 0.7, 0.8, 0.9, 0.99],
            ),
        ]
    )

    res = collection.generate.near_vector(
        near_vector=[0.1, 0.2, 0.3, 0.4, 0.6],
        single_prompt="Is there something to eat in {text}? Only answer yes if there is something to eat or no if not without punctuation",
        grouped_task="Write out the fruit in the order in which they appear in the provided list. Only write the names separated by a space",
        group_by=GroupBy(prop="text", number_of_groups=2, objects_per_group=1),
    )
    assert res.generated == "apples bananas"
    assert len(res.groups) == 2
    assert list(res.groups.values())[0].generated == "Yes"
    assert list(res.groups.values())[1].generated == "No"


def test_openapi_invalid_key(request: SubRequest) -> None:
    local_client = weaviate.connect_to_local(
        port=8086, grpc_port=50057, headers={"X-OpenAI-Api-Key": "IamNotValid"}
    )

    local_client.collections.delete(request.node.name)
    collection = local_client.collections.create(
        name=request.node.name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        generative_config=Configure.Generative.openai(),
    )
    collection.data.insert(properties={"text": "test"})
    with pytest.raises(WeaviateQueryError):
        collection.generate.fetch_objects(single_prompt="tell a joke based on {text}")


def test_openapi_no_module(request: SubRequest) -> None:
    local_client = weaviate.connect_to_local(
        port=8080, grpc_port=50051, headers={"X-OpenAI-Api-Key": "doesnt matter"}
    )

    local_client.collections.delete(request.node.name)
    collection = local_client.collections.create(
        name=request.node.name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        generative_config=Configure.Generative.openai(),
    )
    collection.data.insert(properties={"text": "test"})
    with pytest.raises(WeaviateQueryError):
        collection.generate.fetch_objects(single_prompt="tell a joke based on {text}")


def test_openai_batch_upload(openai_collection: OpenAICollection, request: SubRequest) -> None:
    collection = openai_collection(vectorizer_config=Configure.Vectorizer.text2vec_openai())

    ret = collection.data.insert_many(
        [
            DataObject(properties={"text": "apples are big"}),
            DataObject(properties={"text": "bananas are small"}),
        ]
    )
    if ret.has_errors:
        print(ret.errors)
    assert not ret.has_errors

    objects = collection.query.fetch_objects(include_vector=True).objects
    assert "default" in objects[0].vector
    assert len(objects[0].vector["default"]) > 0


def test_queries_with_rerank_and_generative(collection_factory: CollectionFactory) -> None:
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")

    collection = collection_factory(
        name="Test_test_queries_with_rerank_and_generative",
        generative_config=Configure.Generative.openai(),
        reranker_config=Configure.Reranker.transformers(),
        vectorizer_config=Configure.Vectorizer.text2vec_openai(),
        properties=[Property(name="text", data_type=DataType.TEXT)],
        ports=(8079, 50050),
        headers={"X-OpenAI-Api-Key": api_key},
    )
    if collection._connection._weaviate_version < _ServerVersion(1, 23, 1):
        pytest.skip("Generative reranking requires Weaviate 1.23.1 or higher")

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
                rerank=Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
            ),
            lambda: collection.generate.hybrid(
                "test",
                rerank=Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
            ),
            lambda: collection.generate.near_object(
                uuid1,
                rerank=Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
            ),
            lambda: collection.generate.near_vector(
                vector1["default"],
                rerank=Rerank(prop="text", query="another"),
                single_prompt="What is it? {text}",
            ),
            lambda: collection.generate.near_text(
                "test",
                rerank=Rerank(prop="text", query="another"),
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
