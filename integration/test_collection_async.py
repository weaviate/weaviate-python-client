import datetime
import uuid
from typing import Iterable

import pytest

import weaviate.classes as wvc
from weaviate.collections.classes.config import DataType, Property
from weaviate.collections.classes.data import DataObject
from weaviate.types import UUID

from .conftest import AsyncCollectionFactory, AsyncOpenAICollectionFactory

UUID1 = uuid.UUID("806827e0-2b31-43ca-9269-24fa95a221f9")
UUID2 = uuid.uuid4()
UUID3 = uuid.uuid4()

DATE1 = datetime.datetime.strptime("2012-02-09", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)


@pytest.mark.asyncio
async def test_fetch_objects(async_collection_factory: AsyncCollectionFactory) -> None:
    collection = await async_collection_factory(
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    await collection.data.insert_many(
        [
            {"name": "John Doe"},
        ]
    )

    res = await collection.query.fetch_objects()
    assert len(res.objects) == 1
    assert res.objects[0].properties["name"] == "John Doe"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ids, expected_len, expected",
    [
        ([], 0, set()),
        ((), 0, set()),
        (
            [
                UUID3,
            ],
            1,
            {
                UUID3,
            },
        ),
        ([UUID1, UUID2], 2, {UUID1, UUID2}),
        ((UUID1, UUID3), 2, {UUID1, UUID3}),
        ((UUID1, UUID3, UUID3), 2, {UUID1, UUID3}),
    ],
)
async def test_fetch_objects_by_ids(
    async_collection_factory: AsyncCollectionFactory,
    ids: Iterable[UUID],
    expected_len: int,
    expected: set,
) -> None:
    collection = await async_collection_factory(
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    await collection.data.insert_many(
        [
            DataObject(properties={"name": "first"}, uuid=UUID1),
            DataObject(properties={"name": "second"}, uuid=UUID2),
            DataObject(properties={"name": "third"}, uuid=UUID3),
        ]
    )

    res = await collection.query.fetch_objects_by_ids(ids)
    assert len(res.objects) == expected_len
    assert {o.uuid for o in res.objects} == expected


@pytest.mark.asyncio
async def test_config_update(async_collection_factory: AsyncCollectionFactory) -> None:
    collection = await async_collection_factory(
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        multi_tenancy_config=wvc.config.Configure.multi_tenancy(),
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    await collection.config.update(
        multi_tenancy_config=wvc.config.Reconfigure.multi_tenancy(
            auto_tenant_activation=True,
            auto_tenant_creation=True,
        )
    )


@pytest.mark.asyncio
async def test_config_add_property(async_collection_factory: AsyncCollectionFactory) -> None:
    collection = await async_collection_factory(
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    await collection.config.add_property(Property(name="age", data_type=DataType.INT))


@pytest.mark.asyncio
async def test_config_add_reference(async_collection_factory: AsyncCollectionFactory) -> None:
    collection = await async_collection_factory(
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    await collection.config.add_reference(
        wvc.config.ReferenceProperty(name="test", target_collection=collection.name)
    )


@pytest.mark.asyncio
async def test_references(async_collection_factory: AsyncCollectionFactory) -> None:
    collection = await async_collection_factory(
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    await collection.config.add_reference(
        wvc.config.ReferenceProperty(name="marriage", target_collection=collection.name)
    )
    id1 = await collection.data.insert({"name": "John Doe"})
    id2 = await collection.data.insert({"name": "Jane Doe"})

    await collection.data.reference_add(id1, "marriage", id2)
    await collection.data.reference_add(id2, "marriage", id1)

    res = await collection.query.fetch_object_by_id(
        id1, return_references=wvc.query.QueryReference(link_on="marriage")
    )
    assert res.references["marriage"].objects[0].uuid == id2
    res = await collection.query.fetch_object_by_id(
        id2, return_references=wvc.query.QueryReference(link_on="marriage")
    )
    assert res.references["marriage"].objects[0].uuid == id1

    await collection.data.reference_delete(id1, "marriage", id2)
    res = await collection.query.fetch_object_by_id(
        id1, return_references=wvc.query.QueryReference(link_on="marriage")
    )
    assert len(res.references["marriage"].objects) == 0

    await collection.data.reference_replace(id2, "marriage", id2)
    res = await collection.query.fetch_object_by_id(
        id2, return_references=wvc.query.QueryReference(link_on="marriage")
    )
    assert res.references["marriage"].objects[0].uuid == id2

    await collection.data.reference_add_many(
        [wvc.data.DataReference(from_property="marriage", from_uuid=id1, to_uuid=[id1, id2])]
    )
    res = await collection.query.fetch_object_by_id(
        id1, return_references=wvc.query.QueryReference(link_on="marriage")
    )
    assert len(res.references["marriage"].objects) == 2


@pytest.mark.asyncio
async def test_aggregate(async_collection_factory: AsyncCollectionFactory) -> None:
    collection = await async_collection_factory(
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    await collection.data.insert_many(
        [
            {"name": "John Doe"},
            {"name": "Jane Doe"},
        ]
    )
    res = await collection.aggregate.over_all()
    assert res.total_count == 2

    res = await collection.aggregate.hybrid("John", alpha=0, object_limit=10)
    assert res.total_count == 1


@pytest.mark.asyncio
async def test_iterator(async_collection_factory: AsyncCollectionFactory) -> None:
    collection = await async_collection_factory(
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    await collection.data.insert_many(
        [
            {"name": "John Doe"},
            {"name": "Jane Doe"},
        ]
    )
    names = [obj.properties["name"] async for obj in collection.iterator()]
    assert "John Doe" in names
    assert "Jane Doe" in names


@pytest.mark.asyncio
async def test_delete_many(async_collection_factory: AsyncCollectionFactory) -> None:
    collection = await async_collection_factory(
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    ret = await collection.data.insert_many(
        [
            {"name": "John Doe"},
            {"name": "Jane Doe"},
        ]
    )
    await collection.data.delete_many(wvc.query.Filter.by_property("name").equal("John Doe"))
    assert (await collection.query.fetch_object_by_id(ret.uuids[0])) is None
    assert (await collection.query.fetch_object_by_id(ret.uuids[1])) is not None


@pytest.mark.asyncio
async def test_generate(async_openai_collection: AsyncOpenAICollectionFactory) -> None:
    collection = await async_openai_collection(
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    await collection.data.insert_many(
        [
            {"text": "John Doe"},
            {"text": "Jane Doe"},
        ]
    )
    res = await collection.generate.fetch_objects(
        single_prompt="Who is this? {text}", grouped_task="Who are these people?"
    )
    assert res is not None
    assert res.generated is not None
    assert len(res.objects) == 2
    for obj in res.objects:
        assert obj.generated is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ids, expected_len, expected",
    [
        ([], 0, set()),
        ((), 0, set()),
        (
            [
                UUID3,
            ],
            1,
            {
                UUID3,
            },
        ),
        ([UUID1, UUID2], 2, {UUID1, UUID2}),
        ((UUID1, UUID3), 2, {UUID1, UUID3}),
        ((UUID1, UUID3, UUID3), 2, {UUID1, UUID3}),
    ],
)
async def test_generate_by_ids(
    async_openai_collection: AsyncOpenAICollectionFactory,
    ids: Iterable[UUID],
    expected_len: int,
    expected: set,
) -> None:
    collection = await async_openai_collection(
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    await collection.data.insert_many(
        [
            DataObject(properties={"text": "John Doe"}, uuid=UUID1),
            DataObject(properties={"text": "Jane Doe"}, uuid=UUID2),
            DataObject(properties={"text": "J. Doe"}, uuid=UUID3),
        ]
    )
    res = await collection.generate.fetch_objects_by_ids(
        ids,
        single_prompt="Who is this? {text}",
        grouped_task="Who are these people?",
    )
    assert res is not None
    assert res.generated is not None
    assert len(res.objects) == expected_len
    assert {o.uuid for o in res.objects} == expected
    for obj in res.objects:
        assert obj.generated is not None
