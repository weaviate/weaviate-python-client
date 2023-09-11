import os

import pytest

import weaviate
from weaviate import Config
from weaviate.collection.classes.config import (
    CollectionConfig,
    DataType,
    Property,
    GenerativeFactory,
)
from weaviate.collection.classes.data import DataObject


@pytest.fixture(scope="module")
def client():
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")

    client = weaviate.Client(
        "http://localhost:8080",
        additional_config=Config(grpc_port_experimental=50051),
        additional_headers={"X-OpenAI-Api-Key": api_key},
    )
    client.schema.delete_all()
    yield client
    client.schema.delete_all()


@pytest.mark.parametrize("parameter,answer", [("text", "Yes"), ("content", "No")])
def test_generative_search_single(client, parameter: str, answer: str):
    name = "TestGenerativeSearchOpenAISingle"
    client.collection.delete(name)
    collection = client.collection.create(
        CollectionConfig.create(
            name=name,
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="content", data_type=DataType.TEXT),
            ],
            generative_search=GenerativeFactory.OpenAI(),
        )
    )

    collection.data.insert_many(
        [
            DataObject(properties={"text": "bananas are great", "content": "bananas are bad"}),
            DataObject(properties={"text": "apples are great", "content": "apples are bad"}),
        ]
    )

    res = collection.query.generative(
        prompt_per_object=f"is this good or bad based on {{{parameter}}}? Just answer with yes or no without punctuation"
    )
    for obj in res.objects:
        assert obj.metadata.generative == answer
    assert res.generative_combined_result is None


@pytest.mark.parametrize(
    "prop,answer", [(["text"], "apples bananas"), (["content"], "bananas apples")]
)
def test_generative_search_grouped(client, prop: str, answer: str):
    name = "TestGenerativeSearchOpenAIGroup"
    client.collection.delete(name)
    collection = client.collection.create(
        CollectionConfig.create(
            name=name,
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="content", data_type=DataType.TEXT),
                Property(name="extra", data_type=DataType.TEXT),
            ],
            generative_search=GenerativeFactory.OpenAI(),
        )
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


def test_generative_search_grouped_all_props(client):
    name = "TestGenerativeSearchOpenAIGroupWithProp"
    client.collection.delete(name)
    collection = client.collection.create(
        CollectionConfig.create(
            name=name,
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="content", data_type=DataType.TEXT),
                Property(name="extra", data_type=DataType.TEXT),
            ],
            generative_search=GenerativeFactory.OpenAI(),
        )
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


def test_generative_with_everything(client):
    name = "TestGenerativeSearchOpenAI"
    client.collection.delete(name)
    collection = client.collection.create(
        CollectionConfig.create(
            name=name,
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="content", data_type=DataType.TEXT),
                Property(name="extra", data_type=DataType.TEXT),
            ],
            generative_search=GenerativeFactory.OpenAI(),
        )
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
