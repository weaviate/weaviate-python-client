import os
from typing import Dict

import pytest

from weaviate.collection.classes.config import (
    DataType,
    Property,
    GenerativeFactory,
    VectorizerFactory,
)
from weaviate.collection.classes.data import DataObject
from weaviate.exceptions import WeaviateGRPCException

from .conftest import CollectionObjectFactory


@pytest.fixture(scope="module")
def headers() -> Dict[str, str]:
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")
    return {"X-OpenAI-Api-Key": api_key}


@pytest.mark.parametrize("parameter,answer", [("text", "Yes"), ("content", "No")])
def test_generative_search_single(
    collection_object_factory: CollectionObjectFactory,
    parameter: str,
    answer: str,
    headers: Dict[str, str],
    request_id: str,
):
    collection = collection_object_factory(
        rest_port=8086,
        grpc_port=50057,
        additional_headers=headers,
        name=f"TestGenerativeSearchOpenAISingle{request_id}",
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
        ],
        generative_search=GenerativeFactory.OpenAI(),
    )

    collection.data.insert_many(
        [
            DataObject(properties={"text": "bananas are great", "content": "bananas are bad"}),
            DataObject(properties={"text": "apples are great", "content": "apples are bad"}),
        ]
    )

    res = collection.query.generative(
        prompt_per_object=f"is it good or bad based on {{{parameter}}}? Just answer with yes or no without punctuation"
    )
    for obj in res.objects:
        assert obj.metadata.generative == answer
    assert res.generative_combined_result is None


@pytest.mark.parametrize(
    "prop,answer", [(["text"], "apples bananas"), (["content"], "bananas apples")]
)
def test_generative_search_grouped(
    collection_object_factory: CollectionObjectFactory,
    prop: str,
    answer: str,
    headers: Dict[str, str],
    request_id: str,
):
    collection = collection_object_factory(
        rest_port=8086,
        grpc_port=50057,
        additional_headers=headers,
        name=f"TestGenerativeSearchOpenAIGroup{request_id}",
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="extra", data_type=DataType.TEXT),
        ],
        generative_search=GenerativeFactory.OpenAI(),
    )

    collection.data.insert_many(
        [
            DataObject(properties={"text": "apples are big", "content": "apples are small"}),
            DataObject(properties={"text": "bananas are small", "content": "bananas are big"}),
        ]
    )

    res = collection.query.generative(
        prompt_combined_results="What is big and what is small? write the name of the big thing first and then the name of the small thing after a space.",
        combined_results_properties=prop,
    )
    assert res.generative_combined_result == answer


def test_generative_search_grouped_all_props(
    collection_object_factory: CollectionObjectFactory, headers: Dict[str, str]
):
    collection = collection_object_factory(
        rest_port=8086,
        grpc_port=50057,
        additional_headers=headers,
        name="TestGenerativeSearchOpenAIGroupWithProp",
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="extra", data_type=DataType.TEXT),
        ],
        generative_search=GenerativeFactory.OpenAI(),
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

    res = collection.query.generative(
        prompt_combined_results="What is the biggest and what is the smallest? Only write the names separated by a space"
    )
    assert res.generative_combined_result == "Teddy cats"


def test_generative_with_everything(
    collection_object_factory: CollectionObjectFactory, headers: Dict[str, str]
):
    collection = collection_object_factory(
        rest_port=8086,
        grpc_port=50057,
        additional_headers=headers,
        name="TestGenerativeSearchOpenAI",
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="content", data_type=DataType.TEXT),
            Property(name="extra", data_type=DataType.TEXT),
        ],
        generative_search=GenerativeFactory.OpenAI(),
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

    res = collection.query.generative(
        prompt_per_object="Is there something to eat in {text}? Only answer yes if there is something to eat or no if not without punctuation",
        prompt_combined_results="What is the biggest and what is the smallest? Only write the names separated by a space",
    )
    assert res.generative_combined_result == "Teddy cats"
    for obj in res.objects:
        assert obj.metadata.generative == "Yes"


def test_openapi_invalid_key(collection_object_factory: CollectionObjectFactory):
    collection = collection_object_factory(
        rest_port=8086,
        grpc_port=50057,
        additional_headers={"X-OpenAI-Api-Key": "invalid"},
        name="TestGenerativeSearchOpenAIError",
        properties=[Property(name="text", data_type=DataType.TEXT)],
        generative_search=GenerativeFactory.OpenAI(),
    )
    collection.data.insert(properties={"text": "test"})
    with pytest.raises(WeaviateGRPCException):
        collection.query.generative(prompt_per_object="tell a joke based on {text}")


def test_openapi_no_module(collection_object_factory: CollectionObjectFactory):
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        additional_headers={"X-OpenAI-Api-Key": "doesnt matter"},
        name="TestGenerativeSearchNoModule",
        properties=[Property(name="text", data_type=DataType.TEXT)],
        generative_search=GenerativeFactory.OpenAI(),
    )
    collection.data.insert(properties={"text": "test"})
    with pytest.raises(WeaviateGRPCException):
        collection.query.generative(prompt_per_object="tell a joke based on {text}")


def test_openai_batch_upload(collection_object_factory: CollectionObjectFactory, headers):
    collection = collection_object_factory(
        rest_port=8086,
        grpc_port=50057,
        additional_headers=headers,
        name="TestGenerativeSearchOpenAI",
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ],
        vectorizer_config=VectorizerFactory.text2vec_openai(),
    )

    ret = collection.data.insert_many(
        [
            DataObject(properties={"text": "apples are big"}),
            DataObject(properties={"text": "bananas are small"}),
        ]
    )
    assert not ret.has_errors

    objects = collection.query.get()
    assert objects[0].metadata.vector is not None
    assert len(objects[0].metadata.vector) > 0
