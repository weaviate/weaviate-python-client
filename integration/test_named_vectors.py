from integration.conftest import CollectionFactory, OpenAICollection
import weaviate.classes as wvc

from weaviate.collections.classes.data import DataObject


def test_create_named_vectors(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_contectionary(
                "title", properties=["title"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.text2vec_contectionary(
                name="content", properties=["content"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.text2vec_contectionary(
                name="All", vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.text2vec_contectionary(
                name="AllExplizit", properties=["title", "content"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.none(name="bringYourOwn"),
            wvc.config.Configure.NamedVectors.none(name="bringYourOwn2"),
        ],
    )

    uuid = collection.data.insert(
        properties={"title": "Hello", "content": "World"},
        vector={
            "bringYourOwn": [0.5, 0.25, 0.75],
            "bringYourOwn2": [0.375, 0.625, 0.875],
        },
    )

    obj = collection.query.fetch_object_by_id(
        uuid,
        include_vector=["title", "content", "All", "AllExplizit", "bringYourOwn", "bringYourOwn2"],
    )
    assert obj.vector["title"] is not None
    assert obj.vector["content"] is not None
    assert obj.vector["All"] is not None
    assert obj.vector["bringYourOwn"] == [0.5, 0.25, 0.75]
    assert obj.vector["bringYourOwn2"] == [0.375, 0.625, 0.875]

    # vectorize different data so they must be different
    assert obj.vector["title"] != obj.vector["content"]
    assert obj.vector["title"] != obj.vector["All"]

    # vectorize same data so they must be the same
    assert obj.vector["AllExplizit"] == obj.vector["All"]


def test_batch_add(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_contectionary(
                "title", properties=["title"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.none(name="bringYourOwn"),
        ],
    )

    batch_return = collection.data.insert_many(
        [
            DataObject(
                properties={"title": "Hello", "content": "World"},
                vector={"bringYourOwn": [0.5, 0.25, 0.75]},
            )
        ]
    )
    obj = collection.query.fetch_object_by_id(
        batch_return.uuids[0], include_vector=["title", "bringYourOwn"]
    )
    assert obj.vector["title"] is not None
    # assert obj.vector["bringYourOwn"] == [0.5, 0.25, 0.75]


def test_query(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_contectionary(
                "title", properties=["title"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.text2vec_contectionary(
                name="content", properties=["content"], vectorize_collection_name=False
            ),
        ],
    )

    uuid1 = collection.data.insert(
        properties={"title": "Hello", "content": "World"},
    )

    uuid2 = collection.data.insert(
        properties={"title": "World", "content": "Hello"},
    )

    objs = collection.query.near_text(query="Hello", target_vector="title", distance=0.1).objects
    assert objs[0].uuid == uuid1

    objs = collection.query.near_text(query="Hello", target_vector="content", distance=0.1).objects
    assert objs[0].uuid == uuid2


def test_generate(openai_collection: OpenAICollection) -> None:
    collection = openai_collection(
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_openai(
                "text", properties=["text"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.text2vec_openai(
                name="content", properties=["content"], vectorize_collection_name=False
            ),
        ],
    )

    uuid1 = collection.data.insert(
        properties={"text": "Hello", "content": "World"},
    )

    uuid2 = collection.data.insert(
        properties={"text": "World", "content": "Hello"},
    )

    objs = collection.generate.near_text(
        query="Hello",
        target_vector="text",
        return_metadata=["distance"],
        single_prompt="use {text} and {content} and combine them in the better order without punctuation except whitespace",
        include_vector=["text", "content"],
    ).objects

    assert objs[0].uuid == uuid1
    assert objs[0].generated == "Hello World"

    objs = collection.generate.near_text(
        query="Hello",
        target_vector="content",
        distance=0.1,
        single_prompt="use {text} and {content} and combine them in the better order without punctuation except whitespace",
    ).objects
    assert objs[0].uuid == uuid2
    assert objs[0].generated == "Hello World"
