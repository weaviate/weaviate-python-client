import uuid
from dataclasses import dataclass
from typing import Generator, Optional, Sequence, Union

import pytest

import weaviate
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
    ReferenceProperty,
)
from weaviate.collections.classes.internal import (
    Reference,
    _CrossReference,
    FromReference,
)
from weaviate.collections.classes.tenants import Tenant

UUID = Union[str, uuid.UUID]


@dataclass
class MockNumpyTorch:
    array: list

    def squeeze(self) -> "MockNumpyTorch":
        return self

    def tolist(self) -> list:
        return self.array


@dataclass
class MockTensorFlow:
    array: list

    def numpy(self) -> "MockNumpyTorch":
        return MockNumpyTorch(self.array)


@pytest.fixture(scope="function")
def collection() -> Generator[weaviate.Collection, None, None]:
    client = weaviate.connect_to_local()
    client.collections.delete_all()
    client.collections.create(
        name="CollectionBatchTest",
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
        references=[ReferenceProperty(name="test", target_collection="CollectionBatchTest")],
    )
    yield client.collections.get("CollectionBatchTest")
    client.collections.delete_all()


@pytest.fixture(scope="function")
def mt_collection() -> Generator[weaviate.Collection, None, None]:
    client = weaviate.connect_to_local()
    client.collections.delete_all()
    client.collections.create(
        name="CollectionBatchTestMT",
        properties=[
            ReferenceProperty(name="test", target_collection="CollectionBatchTestMT"),
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    yield client.collections.get("CollectionBatchTestMT")
    client.collections.delete_all()


@pytest.mark.parametrize(
    "vector",
    [None, [1, 2, 3], MockNumpyTorch([1, 2, 3]), MockTensorFlow([1, 2, 3])],
)
@pytest.mark.parametrize("uuid", [None, uuid.uuid4(), str(uuid.uuid4()), uuid.uuid4().hex])
def test_add_object(
    collection: weaviate.Collection, uuid: Optional[UUID], vector: Optional[Sequence]
) -> None:
    with collection.batch as batch:
        batch.add_object(
            properties={},
            uuid=uuid,
            vector=vector,
        )
        assert batch.num_objects() == 1
        assert batch.num_references() == 0
    assert len(batch.failed_objects()) == 0
    assert len(batch.failed_references()) == 0
    objs = collection.query.fetch_objects().objects
    assert len(objs) == 1


@pytest.mark.parametrize("from_uuid", [uuid.uuid4(), str(uuid.uuid4()), uuid.uuid4().hex])
@pytest.mark.parametrize("to_uuid", [uuid.uuid4().hex, uuid.uuid4(), str(uuid.uuid4())])
def test_add_reference(
    collection: weaviate.Collection,
    from_uuid: UUID,
    to_uuid: UUID,
) -> None:
    """Test the `add_reference` method"""

    with collection.batch as batch:
        batch.add_object(uuid=from_uuid)
        assert batch.num_objects() == 1
        assert batch.num_references() == 0
        batch.add_object(uuid=to_uuid)
        assert batch.num_objects() == 2
        assert batch.num_references() == 0
        batch.add_reference(from_uuid=from_uuid, from_property="test", to=Reference.to(to_uuid))
        assert batch.num_objects() == 2
        assert batch.num_references() == 1
    assert len(batch.failed_objects()) == 0
    assert len(batch.failed_references()) == 0
    objs = collection.query.fetch_objects().objects
    obj = collection.query.fetch_object_by_id(
        from_uuid, return_references=FromReference(link_on="test")
    )
    assert len(objs) == 2
    assert isinstance(obj.references["test"], _CrossReference)


def test_add_object_batch_with_tenant(mt_collection: weaviate.Collection) -> None:
    mt_collection.tenants.create([Tenant(name="tenant" + str(i)) for i in range(5)])
    for i in range(5):
        with mt_collection.with_tenant("tenant" + str(i % 5)).batch as batch:
            batch.add_object(
                properties={"name": "tenant" + str(i % 5)},
            )
    assert len(batch.failed_objects()) == 0
    assert len(batch.failed_references()) == 0
    objs = mt_collection.with_tenant("tenant1").query.fetch_objects().objects
    assert len(objs) == 1
    for obj in objs:
        assert obj.properties["name"] == "tenant1"


def test_add_ref_batch_with_tenant(mt_collection: weaviate.Collection) -> None:
    mt_collection.tenants.create([Tenant(name="tenant" + str(i)) for i in range(5)])

    with mt_collection.with_tenant("tenant1").batch as batch:
        obj_uuid0 = uuid.uuid4()
        batch.add_object(properties={"name": "one"}, uuid=obj_uuid0)

        obj_uuid1 = uuid.uuid4()
        batch.add_object(
            properties={"name": "two"},
            uuid=obj_uuid1,
        )

        # add refs between classes for all tenants
        batch.add_reference(
            from_property="test",
            from_uuid=obj_uuid1,
            to=Reference.to_multi_target(obj_uuid0, target_collection="CollectionBatchTestMT"),
        )
        batch.add_reference(
            from_property="test",
            from_uuid=obj_uuid0,
            to=Reference.to_multi_target(obj_uuid1, target_collection="CollectionBatchTestMT"),
        )
        # target collection required when inserting references into multi-tenancy collections
    assert len(batch.failed_objects()) == 0
    assert len(batch.failed_references()) == 0
    ret_obj = mt_collection.with_tenant("tenant1").query.fetch_object_by_id(
        obj_uuid0, return_references=FromReference(link_on="test")
    )
    assert ret_obj.properties["name"] == "one"
    assert isinstance(ret_obj.references["test"], _CrossReference)
