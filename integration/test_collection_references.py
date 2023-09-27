import sys
from typing import TypedDict

import pytest as pytest
import uuid

from weaviate.collection.classes.data import BatchReference, DataObject
from weaviate.collection.classes.grpc import FromReference, FromReferenceMultiTarget


if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated


import weaviate
from weaviate.collection.classes.config import (
    ConfigFactory,
    Property,
    DataType,
    ReferenceProperty,
    ReferencePropertyMultiTarget,
)

from weaviate.collection.classes.internal import Reference, ReferenceFactory
from weaviate.collection.grpc import MetadataQuery


@pytest.fixture(scope="module")
def client():
    connection_params = weaviate.ConnectionParams(
        scheme="http", host="localhost", rest_port=8080, grpc_port=50051
    )
    client = weaviate.Client(connection_params)
    client.schema.delete_all()
    yield client
    client.schema.delete_all()


def test_reference_add_delete_replace(client: weaviate.Client):
    ref_collection = client.collection.create(
        name="RefClass2", vectorizer_config=ConfigFactory.Vectorizer.none()
    )
    uuid_to = ref_collection.data.insert(properties={})
    collection = client.collection.create(
        name="SomethingElse",
        properties=[ReferenceProperty(name="ref", target_collection="RefClass2")],
        vectorizer_config=ConfigFactory.Vectorizer.none(),
    )

    uuid_from1 = collection.data.insert({}, uuid.uuid4())
    uuid_from2 = collection.data.insert({"ref": ReferenceFactory.to(uuids=uuid_to)}, uuid.uuid4())
    collection.data.reference_add(
        from_uuid=uuid_from1, from_property="ref", ref=ReferenceFactory.to(uuids=uuid_to)
    )

    collection.data.reference_delete(
        from_uuid=uuid_from1, from_property="ref", ref=ReferenceFactory.to(uuids=uuid_to)
    )
    assert len(collection.query.fetch_object_by_id(uuid_from1).properties["ref"]) == 0

    collection.data.reference_add(
        from_uuid=uuid_from2, from_property="ref", ref=ReferenceFactory.to(uuids=uuid_to)
    )
    obj = collection.query.fetch_object_by_id(uuid_from2)
    assert len(obj.properties["ref"]) == 2
    assert str(uuid_to) in "".join([ref["beacon"] for ref in obj.properties["ref"]])

    collection.data.reference_replace(
        from_uuid=uuid_from2, from_property="ref", ref=ReferenceFactory.to(uuids=[])
    )
    assert len(collection.query.fetch_object_by_id(uuid_from2).properties["ref"]) == 0

    client.collection.delete("SomethingElse")
    client.collection.delete("RefClass2")


def test_mono_references_grpc(client: weaviate.Client):
    A = client.collection.create(
        name="A",
        vectorizer_config=ConfigFactory.Vectorizer.none(),
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
    )
    uuid_A1 = A.data.insert(properties={"Name": "A1"})
    uuid_A2 = A.data.insert(properties={"Name": "A2"})

    objects = A.query.bm25(query="A1", return_properties="name").objects
    assert objects[0].properties["name"] == "A1"

    B = client.collection.create(
        name="B",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferenceProperty(name="ref", target_collection="A"),
        ],
        vectorizer_config=ConfigFactory.Vectorizer.none(),
    )
    uuid_B = B.data.insert({"Name": "B", "ref": ReferenceFactory.to(uuids=uuid_A1)})
    B.data.reference_add(
        from_uuid=uuid_B, from_property="ref", ref=ReferenceFactory.to(uuids=uuid_A2)
    )

    objects = B.query.bm25(
        query="B",
        return_properties=FromReference(
            link_on="ref",
            return_properties=["name"],
        ),
    ).objects
    assert objects[0].properties["ref"].objects[0].properties["name"] == "A1"
    assert objects[0].properties["ref"].objects[1].properties["name"] == "A2"

    objects = B.query.bm25(
        query="B",
        return_properties=[
            FromReference(
                link_on="ref",
                return_properties=["name"],
                return_metadata=MetadataQuery(uuid=True),
            )
        ],
    ).objects
    assert objects[0].properties["ref"].objects[0].properties["name"] == "A1"
    assert objects[0].properties["ref"].objects[0].metadata.uuid == uuid_A1
    assert objects[0].properties["ref"].objects[1].properties["name"] == "A2"
    assert objects[0].properties["ref"].objects[1].metadata.uuid == uuid_A2

    C = client.collection.create(
        name="C",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferenceProperty(name="ref", target_collection="B"),
        ],
        vectorizer_config=ConfigFactory.Vectorizer.none(),
    )
    C.data.insert({"Name": "find me", "ref": ReferenceFactory.to(uuids=uuid_B)})

    objects = C.query.bm25(
        query="find",
        return_properties=[
            "name",
            FromReference(
                link_on="ref",
                return_properties=[
                    "name",
                    FromReference(
                        link_on="ref",
                        return_properties=["name"],
                        return_metadata=MetadataQuery(uuid=True),
                    ),
                ],
                return_metadata=MetadataQuery(uuid=True, last_update_time_unix=True),
            ),
        ],
    ).objects
    assert objects[0].properties["name"] == "find me"
    assert objects[0].properties["ref"].objects[0].properties["name"] == "B"
    assert (
        objects[0].properties["ref"].objects[0].properties["ref"].objects[0].properties["name"]
        == "A1"
    )
    assert (
        objects[0].properties["ref"].objects[0].properties["ref"].objects[1].properties["name"]
        == "A2"
    )


def test_mono_references_grpc_typed_dicts(client: weaviate.Client):
    client.collection.delete("ATypedDicts")
    client.collection.delete("BTypedDicts")
    client.collection.delete("CTypedDicts")

    class AProps(TypedDict):
        name: str

    class BProps(TypedDict):
        name: str
        ref: Annotated[Reference[AProps], MetadataQuery(uuid=True)]

    class CProps(TypedDict):
        name: str
        ref: Annotated[Reference[BProps], MetadataQuery(uuid=True)]

    client.collection.create(
        name="ATypedDicts",
        vectorizer_config=ConfigFactory.Vectorizer.none(),
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
    )
    A = client.collection.get("ATypedDicts", AProps)
    uuid_A1 = A.data.insert(AProps(name="A1"))
    uuid_A2 = A.data.insert(AProps(name="A2"))

    B = client.collection.create(
        name="BTypedDicts",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferenceProperty(name="ref", target_collection="ATypedDicts"),
        ],
        vectorizer_config=ConfigFactory.Vectorizer.none(),
    )
    B = client.collection.get("BTypedDicts", BProps)
    uuid_B = B.data.insert(
        properties=BProps(name="B", ref=ReferenceFactory.to(uuids=uuid_A1, data_model=AProps))
    )
    B.data.reference_add(
        from_uuid=uuid_B,
        from_property="ref",
        ref=ReferenceFactory.to(uuids=uuid_A2, data_model=AProps),
    )

    client.collection.create(
        name="CTypedDicts",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            Property(name="Age", data_type=DataType.INT),
            ReferenceProperty(name="ref", target_collection="BTypedDicts"),
        ],
        vectorizer_config=ConfigFactory.Vectorizer.none(),
    )
    C = client.collection.get("CTypedDicts", CProps)
    C.data.insert(
        properties=CProps(name="find me", ref=ReferenceFactory.to(uuids=uuid_B, data_model=BProps))
    )

    objects = (
        client.collection.get("CTypedDicts")
        .query.bm25(
            query="find",
            return_properties=CProps,
        )
        .objects
    )
    assert (
        objects[0].properties["name"] == "find me"
    )  # happy path (in type and in return_properties)
    assert objects[0].metadata.uuid is None
    assert (
        objects[0].properties.get("not_specified") is None
    )  # type is str but instance is None (in type but not in return_properties)
    assert objects[0].properties["ref"].objects[0].properties["name"] == "B"
    assert objects[0].properties["ref"].objects[0].metadata.uuid == uuid_B
    assert (
        objects[0].properties["ref"].objects[0].properties["ref"].objects[0].properties["name"]
        == "A1"
    )
    assert (
        objects[0].properties["ref"].objects[0].properties["ref"].objects[0].metadata.uuid
        == uuid_A1
    )
    assert (
        objects[0].properties["ref"].objects[0].properties["ref"].objects[1].properties["name"]
        == "A2"
    )
    assert (
        objects[0].properties["ref"].objects[0].properties["ref"].objects[1].metadata.uuid
        == uuid_A2
    )


def test_multi_references_grpc(client: weaviate.Client):
    client.collection.delete("A")
    client.collection.delete("B")
    client.collection.delete("C")

    A = client.collection.create(
        name="A",
        vectorizer_config=ConfigFactory.Vectorizer.none(),
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
    )
    uuid_A = A.data.insert(properties={"Name": "A"})

    B = client.collection.create(
        name="B",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
        vectorizer_config=ConfigFactory.Vectorizer.none(),
    )
    uuid_B = B.data.insert({"Name": "B"})

    C = client.collection.create(
        name="C",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferencePropertyMultiTarget(name="ref", target_collections=["A", "B"]),
        ],
        vectorizer_config=ConfigFactory.Vectorizer.none(),
    )
    C.data.insert(
        {
            "Name": "first",
            "ref": ReferenceFactory.to_multi_target(uuids=uuid_A, target_collection="A"),
        }
    )
    C.data.insert(
        {
            "Name": "second",
            "ref": ReferenceFactory.to_multi_target(uuids=uuid_B, target_collection="B"),
        }
    )

    objects = C.query.bm25(
        query="first",
        return_properties=[
            "name",
            FromReferenceMultiTarget(
                link_on="ref",
                target_collection="A",
                return_properties=["name"],
                return_metadata=MetadataQuery(uuid=True, last_update_time_unix=True),
            ),
        ],
    ).objects
    assert objects[0].properties["name"] == "first"
    assert len(objects[0].properties["ref"].objects) == 1
    assert objects[0].properties["ref"].objects[0].properties["name"] == "A"

    objects = C.query.bm25(
        query="second",
        return_properties=[
            "name",
            FromReferenceMultiTarget(
                link_on="ref",
                target_collection="B",
                return_properties=[
                    "name",
                ],
                return_metadata=MetadataQuery(uuid=True, last_update_time_unix=True),
            ),
        ],
    ).objects
    assert objects[0].properties["name"] == "second"
    assert len(objects[0].properties["ref"].objects) == 1
    assert objects[0].properties["ref"].objects[0].properties["name"] == "B"

    client.collection.delete("A")
    client.collection.delete("B")
    client.collection.delete("C")


def test_references_batch(client: weaviate.Client):
    name_ref_to = "TestBatchRefTo"
    name_ref_from = "TestBatchRefFrom"

    client.collection.delete(name_ref_to)
    client.collection.delete(name_ref_from)

    ref_collection = client.collection.create(
        name=name_ref_to,
        vectorizer_config=ConfigFactory.Vectorizer.none(),
        properties=[Property(name="num", data_type=DataType.INT)],
    )
    num_objects = 10

    uuids_to = ref_collection.data.insert_many(
        [DataObject(properties={"num": i}) for i in range(num_objects)]
    ).uuids.values()
    collection = client.collection.create(
        name=name_ref_from,
        properties=[
            ReferenceProperty(name="ref", target_collection=name_ref_to),
            Property(name="num", data_type=DataType.INT),
        ],
        vectorizer_config=ConfigFactory.Vectorizer.none(),
    )
    uuids_from = collection.data.insert_many(
        [DataObject(properties={"num": i}) for i in range(num_objects)]
    ).uuids.values()

    batch_return = collection.data.reference_add_many(
        from_property="ref",
        refs=[
            BatchReference(from_uuid=list(uuids_from)[i], to_uuid=list(uuids_to)[i])
            for i in range(num_objects)
        ],
    )

    assert batch_return is None

    objects = collection.query.fetch_objects(
        return_properties=[
            "num",
            FromReference(link_on="ref"),
        ],
    ).objects

    for obj in objects:
        assert obj.properties["num"] == obj.properties["ref"].objects[0].properties["num"]


def test_references_batch_with_errors(client: weaviate.Client):
    name_ref_to = "TestBatchRefErrorTo"
    name_ref_from = "TestBatchRefErrorFrom"

    client.collection.delete(name_ref_to)
    client.collection.delete(name_ref_from)

    _ = client.collection.create(
        name=name_ref_to,
        vectorizer_config=ConfigFactory.Vectorizer.none(),
    )

    collection = client.collection.create(
        name=name_ref_from,
        properties=[
            ReferenceProperty(name="ref", target_collection=name_ref_to),
            Property(name="num", data_type=DataType.INT),
        ],
        vectorizer_config=ConfigFactory.Vectorizer.none(),
    )

    batch_return = collection.data.reference_add_many(
        from_property="doesNotExist",
        refs=[BatchReference(from_uuid=uuid.uuid4(), to_uuid=uuid.uuid4())],
    )
    assert batch_return is not None
    assert 0 in batch_return
    assert (
        batch_return[0][0].message
        == "property doesNotExist does not exist for class TestBatchRefErrorFrom"
    )


def test_references_with_string_syntax(client: weaviate.Client):
    name1 = "TestReferencesWithStringSyntaxA"
    name2 = "TestReferencesWithStringSyntaxB"
    client.collection.delete(name1)
    client.collection.delete(name2)

    client.collection.create(
        name=name1,
        vectorizer_config=ConfigFactory.Vectorizer.none(),
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            Property(name="Age", data_type=DataType.INT),
            Property(name="Weird__Name", data_type=DataType.INT),
        ],
    )

    uuid_A = client.collection.get(name1).data.insert(
        properties={"Name": "A", "Age": 1, "Weird__Name": 2}
    )

    client.collection.get(name1).query.fetch_object_by_id(uuid_A)

    client.collection.create(
        name=name2,
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferenceProperty(name="ref", target_collection=name1),
        ],
        vectorizer_config=ConfigFactory.Vectorizer.none(),
    )

    client.collection.get(name2).data.insert(
        {"Name": "B", "ref": ReferenceFactory.to(uuids=uuid_A)}
    )

    objects = (
        client.collection.get(name2)
        .query.bm25(
            query="B",
            return_properties=[
                "name",
                "__ref__properties__Name",
                "__ref__properties__Age",
                "__ref__properties__Weird__Name",
                "__ref__metadata__uuid",
                "__ref__metadata__last_update_time_unix",
            ],
        )
        .objects
    )

    assert objects[0].properties["name"] == "B"
    assert objects[0].properties["ref"].objects[0].properties["name"] == "A"
    assert objects[0].properties["ref"].objects[0].properties["age"] == 1
    assert objects[0].properties["ref"].objects[0].properties["weird__Name"] == 2
    assert objects[0].properties["ref"].objects[0].metadata.uuid == uuid_A
    assert objects[0].properties["ref"].objects[0].metadata.last_update_time_unix is not None
