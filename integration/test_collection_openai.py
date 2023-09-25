import os
from typing import List

import pytest

import weaviate
from weaviate import Config
from weaviate.collection.classes.config import (
    ConfigFactory,
    DataType,
    Property,
)
from weaviate.collection.classes.data import DataObject
from weaviate.collection.classes.grpc import MetadataQuery
from weaviate.exceptions import WeaviateGRPCException


@pytest.fixture(scope="module")
def client():
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")

    client = weaviate.Client(
        "http://localhost:8086",
        additional_config=Config(grpc_port_experimental=50057),  # ports with generative module
        additional_headers={"X-OpenAI-Api-Key": api_key},
    )
    client.schema.delete_all()
    yield client
    client.schema.delete_all()


@pytest.mark.parametrize("parameter,answer", [("text", "Yes"), ("content", "No")])
def test_generative_search_single(client: weaviate.Client, parameter: str, answer: str):
    name = "TestGenerativeSearchOpenAISingle"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
        ],
        generative_config=ConfigFactory.Generative.openai(),
    )

    collection.data.insert_many(
        [
            DataObject(properties={"text": "bananas are great", "content": "bananas are bad"}),
            DataObject(properties={"text": "apples are great", "content": "apples are bad"}),
        ]
    )

    res = collection.generate.fetch_objects(
        single_prompt=f"is it good or bad based on {{{parameter}}}? Just answer with yes or no without punctuation"
    )
    for obj in res.objects:
        assert obj.metadata.generative == answer
    assert res.generated is None


@pytest.mark.parametrize(
    "prop,answer", [(["text"], "apples bananas"), (["content"], "bananas apples")]
)
def test_fetch_objects_generate_search_grouped(
    client: weaviate.Client, prop: List[str], answer: str
):
    name = "TestGenerativeSearchOpenAIGroup"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="extra", data_type=DataType.TEXT),
        ],
        generative_config=ConfigFactory.Generative.openai(),
    )

    collection.data.insert_many(
        [
            DataObject(properties={"text": "apples are big", "content": "apples are small"}),
            DataObject(properties={"text": "bananas are small", "content": "bananas are big"}),
        ]
    )

    res = collection.generate.fetch_objects(
        grouped_task="What is big and what is small? write the name of the big thing first and then the name of the small thing after a space.",
        grouped_properties=prop,
    )
    assert res.generated == answer


def test_fetch_objects_generate_search_grouped_all_props(client: weaviate.Client):
    name = "TestGenerativeSearchOpenAIGroupWithProp"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="extra", data_type=DataType.TEXT),
        ],
        generative_config=ConfigFactory.Generative.openai(),
    )

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
        grouped_task="What is the biggest and what is the smallest? Only write the names separated by a space"
    )
    assert res.generated == "Teddy cats"


def test_fetch_objects_generate_search_grouped_specified_prop(client: weaviate.Client):
    name = "TestGenerativeSearchOpenAIGroupWithProp"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="extra", data_type=DataType.TEXT),
        ],
        generative_config=ConfigFactory.Generative.openai(),
    )

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


def test_fetch_objects_generate_with_everything(client: weaviate.Client):
    name = "TestGetGenerativeSearchOpenAI"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="extra", data_type=DataType.TEXT),
        ],
        generative_config=ConfigFactory.Generative.openai(),
    )

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
        single_prompt="Is there something to eat in {text}? Only answer yes if there is something to eat or no if not without punctuation",
        grouped_task="What is the biggest and what is the smallest? Only write the names separated by a space",
    )
    assert res.generated == "Teddy cats"
    for obj in res.objects:
        assert obj.metadata.generative == "Yes"


def test_bm25_generate_with_everything(client: weaviate.Client):
    name = "TestBM25GenerativeSearchOpenAI"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="extra", data_type=DataType.TEXT),
        ],
        generative_config=ConfigFactory.Generative.openai(),
    )

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
        assert obj.metadata.generative == "Yes"


def test_hybrid_generate_with_everything(client: weaviate.Client):
    name = "TestHybridGenerativeSearchOpenAI"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="extra", data_type=DataType.TEXT),
        ],
        generative_config=ConfigFactory.Generative.openai(),
    )

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
                    "text": "cats are small",
                    "content": "bananas are the smallest and smaller than everything else",
                }
            ),
        ]
    )

    res = collection.generate.hybrid(
        query="cats",
        query_properties=["text"],
        single_prompt="Is there something to eat in {text}? Only answer yes if there is something to eat or no if not without punctuation",
        grouped_task="What is the biggest and what is the smallest? Only write the names separated by a space from biggest to smallest",
    )
    assert res.generated == "cats bananas"
    for obj in res.objects:
        assert obj.metadata.generative == "No"


def test_near_text_generate_with_everything(client: weaviate.Client):
    name = "TestNearTextGenerativeSearchOpenAI"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="extra", data_type=DataType.TEXT),
        ],
        generative_config=ConfigFactory.Generative.openai(),
        vectorizer_config=ConfigFactory.Vectorizer.text2vec_openai(vectorize_class_name=False),
    )

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
                    "text": "cats are small",
                    "content": "bananas are the smallest and smaller than everything else",
                }
            ),
        ]
    )

    res = collection.generate.near_text(
        query="small fruit",
        single_prompt="Is there something to eat in {text}? Only answer yes if there is something to eat or no if not without punctuation",
        grouped_task="Write out the fruit in the order in which they appear in the provided list. Only write the names separated by a space",
    )
    assert res.generated == "bananas apples"
    assert res.objects[0].metadata.generative == "No"
    assert res.objects[1].metadata.generative == "Yes"


def test_near_vector_generate_with_everything(client: weaviate.Client):
    name = "TestNearTextGenerativeSearchOpenAI"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="extra", data_type=DataType.TEXT),
        ],
        generative_config=ConfigFactory.Generative.openai(),
    )

    collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "apples are big",
                    "content": "Teddy is the biggest and bigger than everything else",
                },
                vector=[1, 2, 3, 4, 5],
            ),
            DataObject(
                properties={
                    "text": "cats are small",
                    "content": "bananas are the smallest and smaller than everything else",
                },
                vector=[6, 7, 8, 9, 10],
            ),
        ]
    )

    res = collection.generate.near_vector(
        near_vector=[1, 2, 3, 4, 6],
        single_prompt="Is there something to eat in {text}? Only answer yes if there is something to eat or no if not without punctuation",
        grouped_task="Write out the fruit in the order in which they appear in the provided list. Only write the names separated by a space",
    )
    assert res.generated == "apples bananas"
    assert res.objects[0].metadata.generative == "Yes"
    assert res.objects[1].metadata.generative == "No"


def test_openapi_invalid_key():
    local_client = weaviate.Client(
        "http://localhost:8086",
        additional_config=Config(grpc_port_experimental=50057),
        additional_headers={"X-OpenAI-Api-Key": "IamNotValid"},
    )

    name = "TestGenerativeSearchOpenAIError"
    local_client.collection.delete(name)
    collection = local_client.collection.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        generative_config=ConfigFactory.Generative.openai(),
    )
    collection.data.insert(properties={"text": "test"})
    with pytest.raises(WeaviateGRPCException):
        collection.generate.fetch_objects(single_prompt="tell a joke based on {text}")


def test_openapi_no_module():
    local_client = weaviate.Client(
        "http://localhost:8080",  # main version that does not have a generative module
        additional_config=Config(grpc_port_experimental=50051),
        additional_headers={"X-OpenAI-Api-Key": "doesnt matter"},
    )

    name = "TestGenerativeSearchNoModule"
    local_client.collection.delete(name)
    collection = local_client.collection.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        generative_config=ConfigFactory.Generative.openai(),
    )
    collection.data.insert(properties={"text": "test"})
    with pytest.raises(WeaviateGRPCException):
        collection.generate.fetch_objects(single_prompt="tell a joke based on {text}")


def test_openai_batch_upload(client: weaviate.Client):
    name = "TestGenerativeSearchOpenAIBatch"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ],
        vectorizer_config=ConfigFactory.Vectorizer.text2vec_openai(),
    )

    ret = collection.data.insert_many(
        [
            DataObject(properties={"text": "apples are big"}),
            DataObject(properties={"text": "bananas are small"}),
        ]
    )
    assert not ret.has_errors

    objects = collection.query.fetch_objects(return_metadata=MetadataQuery(vector=True))
    assert objects[0].metadata.vector is not None
    assert len(objects[0].metadata.vector) > 0
