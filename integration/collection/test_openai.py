import pytest

from weaviate.collection import Collection
from weaviate.collection.classes.config import (
    DataType,
    Property,
    GenerativeFactory,
    VectorizerFactory,
)
from weaviate.collection.classes.data import DataObject
from weaviate.exceptions import WeaviateGRPCException


@pytest.mark.parametrize("parameter,answer", [("text", "Yes"), ("content", "No")])
def test_generative_search_single(collection_openai: Collection, parameter: str, answer: str):
    name = "TestGenerativeSearchOpenAISingle"
    collection_openai.delete(name)
    collection = collection_openai.create(
        name=name,
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
def test_generative_search_grouped(collection_openai: Collection, prop: str, answer: str):
    name = "TestGenerativeSearchOpenAIGroup"
    collection_openai.delete(name)
    collection = collection_openai.create(
        name=name,
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


def test_generative_search_grouped_all_props(collection_openai: Collection):
    name = "TestGenerativeSearchOpenAIGroupWithProp"
    collection_openai.delete(name)
    collection = collection_openai.create(
        name=name,
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


def test_generative_with_everything(collection_openai: Collection):
    name = "TestGenerativeSearchOpenAI"
    collection_openai.delete(name)
    collection = collection_openai.create(
        name=name,
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


def test_openapi_invalid_key(collection_openai_invalid_key: Collection):
    name = "TestGenerativeSearchOpenAIError"
    collection_openai_invalid_key.delete(name)
    collection = collection_openai_invalid_key.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        generative_search=GenerativeFactory.OpenAI(),
    )
    collection.data.insert(properties={"text": "test"})
    with pytest.raises(WeaviateGRPCException):
        collection.query.generative(prompt_per_object="tell a joke based on {text}")


def test_openapi_no_module(collection_openai_no_module: Collection):
    name = "TestGenerativeSearchNoModule"
    collection_openai_no_module.delete(name)
    collection = collection_openai_no_module.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        generative_search=GenerativeFactory.OpenAI(),
    )
    collection.data.insert(properties={"text": "test"})
    with pytest.raises(WeaviateGRPCException):
        collection.query.generative(prompt_per_object="tell a joke based on {text}")


def test_openai_batch_upload(collection_openai: Collection):
    name = "TestGenerativeSearchOpenAI"
    collection_openai.delete(name)
    collection = collection_openai.create(
        name=name,
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
