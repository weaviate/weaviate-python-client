import uuid
from typing import Dict, TypedDict

import pytest as pytest
from typing_extensions import Annotated

from integration.conftest import CollectionFactory, CollectionFactoryGet
from weaviate.collections.classes.config import (
    Configure,
    Property,
    DataType,
    ReferenceProperty,
)
from weaviate.collections.classes.data import DataObject, DataReference
from weaviate.collections.classes.grpc import (
    MetadataQuery,
    QueryReference,
)
from weaviate.collections.classes.internal import (
    CrossReference,
    ReferenceToMulti,
    CrossReferenceAnnotation,
    ReferenceInput,
    SingleReferenceInput,
)
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.types import UUID

TO_UUID = uuid.UUID("8ad0d33c-8db1-4437-87f3-72161ca2a51a")
TO_UUID2 = uuid.UUID("577887c1-4c6b-5594-aa62-f0c17883d9cf")


@pytest.mark.parametrize("add", [TO_UUID, str(TO_UUID)])
@pytest.mark.parametrize("delete", [TO_UUID, str(TO_UUID)])
def test_reference_add_delete_replace(
    collection_factory: CollectionFactory,
    add: SingleReferenceInput,
    delete: SingleReferenceInput,
) -> None:
    ref_collection = collection_factory(
        name="Target", vectorizer_config=Configure.Vectorizer.none()
    )
    ref_collection.data.insert(properties={}, uuid=TO_UUID)
    collection = collection_factory(
        references=[
            ReferenceProperty.MultiTarget(name="ref", target_collections=[ref_collection.name])
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    uuid_from1 = collection.data.insert({}, uuid=uuid.uuid4())
    uuid_from2 = collection.data.insert({}, references={"ref": TO_UUID}, uuid=uuid.uuid4())
    collection.data.reference_add(from_uuid=uuid_from1, from_property="ref", to=add)

    collection.data.reference_delete(from_uuid=uuid_from1, from_property="ref", to=delete)
    assert (
        len(
            collection.query.fetch_object_by_id(
                uuid_from1, return_references=QueryReference(link_on="ref")
            )
            .references["ref"]
            .objects
        )
        == 0
    )

    collection.data.reference_add(from_uuid=uuid_from2, from_property="ref", to=add)
    obj = collection.query.fetch_object_by_id(
        uuid_from2, return_references=QueryReference(link_on="ref")
    )
    assert obj is not None
    assert len(obj.references["ref"].objects) == 2
    assert TO_UUID in [x.uuid for x in obj.references["ref"].objects]

    collection.data.reference_replace(from_uuid=uuid_from2, from_property="ref", to=[])
    assert (
        len(
            collection.query.fetch_object_by_id(
                uuid_from2, return_references=QueryReference(link_on="ref")
            )
            .references["ref"]
            .objects
        )
        == 0
    )


def test_reference_add_delete_replace_multi_target(
    collection_factory: CollectionFactory,
) -> None:
    ref_collection = collection_factory(
        name="Target", vectorizer_config=Configure.Vectorizer.none()
    )
    ref_collection.data.insert(properties={}, uuid=TO_UUID)
    collection = collection_factory(
        references=[
            ReferenceProperty.MultiTarget(name="ref", target_collections=[ref_collection.name])
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    uuid_from1 = collection.data.insert({}, uuid=uuid.uuid4())
    uuid_from2 = collection.data.insert({}, references={"ref": TO_UUID}, uuid=uuid.uuid4())
    collection.data.reference_add(
        from_uuid=uuid_from1,
        from_property="ref",
        to=ReferenceToMulti(target_collection=ref_collection.name, uuids=TO_UUID),
    )

    collection.data.reference_delete(
        from_uuid=uuid_from1,
        from_property="ref",
        to=ReferenceToMulti(target_collection=ref_collection.name, uuids=TO_UUID),
    )
    assert (
        len(
            collection.query.fetch_object_by_id(
                uuid_from1, return_references=QueryReference(link_on="ref")
            )
            .references["ref"]
            .objects
        )
        == 0
    )

    collection.data.reference_add(
        from_uuid=uuid_from2,
        from_property="ref",
        to=ReferenceToMulti(target_collection=ref_collection.name, uuids=TO_UUID),
    )
    obj = collection.query.fetch_object_by_id(
        uuid_from2, return_references=QueryReference(link_on="ref")
    )
    assert obj is not None
    assert len(obj.references["ref"].objects) == 2
    assert TO_UUID in [x.uuid for x in obj.references["ref"].objects]

    collection.data.reference_replace(
        from_uuid=uuid_from2,
        from_property="ref",
        to=ReferenceToMulti(target_collection=ref_collection.name, uuids=[]),
    )
    assert (
        len(
            collection.query.fetch_object_by_id(
                uuid_from2, return_references=QueryReference(link_on="ref")
            )
            .references["ref"]
            .objects
        )
        == 0
    )


@pytest.mark.parametrize(
    "to",
    [
        [TO_UUID, TO_UUID],
        ReferenceToMulti(target_collection="Target", uuids=[TO_UUID, TO_UUID]),
    ],
)
def test_reference_add_multiple_uuids_error(
    collection_factory: CollectionFactory, to: SingleReferenceInput
) -> None:
    ref_collection = collection_factory(
        name="Target", vectorizer_config=Configure.Vectorizer.none()
    )
    ref_collection.data.insert(properties={}, uuid=TO_UUID)
    collection = collection_factory(
        references=[ReferenceProperty(name="ref", target_collection=ref_collection.name)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid_from1 = collection.data.insert({}, uuid=uuid.uuid4())
    with pytest.raises(WeaviateInvalidInputError):
        collection.data.reference_add(from_uuid=uuid_from1, from_property="ref", to=to)


@pytest.mark.parametrize(
    "to",
    [
        [TO_UUID, TO_UUID],
        ReferenceToMulti(target_collection="Target", uuids=[TO_UUID, TO_UUID]),
    ],
)
def test_reference_delete_multiple_uuids_error(
    collection_factory: CollectionFactory, to: SingleReferenceInput
) -> None:
    ref_collection = collection_factory(
        name="Target", vectorizer_config=Configure.Vectorizer.none()
    )
    ref_collection.data.insert(properties={}, uuid=TO_UUID)
    collection = collection_factory(
        references=[ReferenceProperty(name="ref", target_collection=ref_collection.name)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid_from1 = collection.data.insert({}, uuid=uuid.uuid4())
    with pytest.raises(WeaviateInvalidInputError):
        collection.data.reference_delete(from_uuid=uuid_from1, from_property="ref", to=to)


def test_mono_references_grpc(collection_factory: CollectionFactory) -> None:
    A = collection_factory(
        name="A",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
    )
    uuid_A1 = A.data.insert(properties={"Name": "A1"})
    uuid_A2 = A.data.insert(properties={"Name": "A2"})

    a_objs = A.query.bm25(query="A1", return_properties="name").objects
    assert a_objs[0].collection == A.name
    assert a_objs[0].properties["name"] == "A1"

    B = collection_factory(
        name="B",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        references=[
            ReferenceProperty(name="a", target_collection=A.name),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid_B = B.data.insert({"Name": "B"}, references={"a": uuid_A1})
    B.data.reference_add(from_uuid=uuid_B, from_property="a", to=uuid_A2)

    b_objs = B.query.bm25(
        query="B",
        return_references=QueryReference(
            link_on="a",
            return_properties=["name"],
        ),
    ).objects
    assert b_objs[0].references["a"].objects[0].collection == A.name
    assert b_objs[0].references["a"].objects[0].properties["name"] == "A1"
    assert b_objs[0].references["a"].objects[0].uuid == uuid_A1
    assert b_objs[0].references["a"].objects[1].collection == A.name
    assert b_objs[0].references["a"].objects[1].properties["name"] == "A2"
    assert b_objs[0].references["a"].objects[1].uuid == uuid_A2

    C = collection_factory(
        name="C",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        references=[
            ReferenceProperty(name="b", target_collection=B.name),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    C.data.insert({"Name": "find me"}, references={"b": uuid_B})

    c_objs = C.query.bm25(
        query="find",
        return_properties="name",
        return_references=QueryReference(
            link_on="b",
            return_properties="name",
            return_metadata=MetadataQuery(last_update_time=True),
            return_references=QueryReference(
                link_on="a",
                return_properties="name",
            ),
        ),
    ).objects
    assert c_objs[0].collection == C.name
    assert c_objs[0].properties["name"] == "find me"
    assert c_objs[0].references["b"].objects[0].collection == B.name
    assert c_objs[0].references["b"].objects[0].properties["name"] == "B"
    assert c_objs[0].references["b"].objects[0].metadata.last_update_time is not None
    assert c_objs[0].references["b"].objects[0].references["a"].objects[0].collection == A.name
    assert (
        c_objs[0].references["b"].objects[0].references["a"].objects[0].properties["name"] == "A1"
    )
    assert c_objs[0].references["b"].objects[0].references["a"].objects[1].collection == A.name
    assert (
        c_objs[0].references["b"].objects[0].references["a"].objects[1].properties["name"] == "A2"
    )


@pytest.mark.parametrize("level", ["col-col", "col-query", "query-col", "query-query"])
def test_mono_references_grpc_with_generics(
    collection_factory: CollectionFactory,
    collection_factory_get: CollectionFactoryGet,
    level: str,
) -> None:
    class AProps(TypedDict):
        name: str

    class BProps(TypedDict):
        name: str

    class BRefs(TypedDict):
        a: Annotated[
            CrossReference[AProps, None],
            CrossReferenceAnnotation(
                metadata=MetadataQuery(creation_time=True), include_vector=True
            ),
        ]

    class CProps(TypedDict):
        name: str

    class CRefs(TypedDict):
        b: CrossReference[BProps, BRefs]

    dummy_a = collection_factory(
        name="a",
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
    )
    A = collection_factory_get(dummy_a.name, AProps)
    uuid_A1 = A.data.insert(AProps(name="A1"))
    uuid_A2 = A.data.insert(AProps(name="A2"))

    dummy_b = collection_factory(
        name="B",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        references=[
            ReferenceProperty(name="a", target_collection=A.name),
        ],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    B = collection_factory_get(dummy_b.name, BProps)
    uuid_B = B.data.insert(properties={"name": "B"}, references={"a": uuid_A1})
    B.data.reference_add(
        from_uuid=uuid_B,
        from_property="a",
        to=uuid_A2,
    )

    b_objs = B.query.bm25(query="B", return_references=BRefs).objects
    assert b_objs[0].collection == B.name
    assert b_objs[0].properties["name"] == "B"
    assert b_objs[0].references["a"].objects[0].collection == A.name
    assert b_objs[0].references["a"].objects[0].properties["name"] == "A1"
    assert b_objs[0].references["a"].objects[0].uuid == uuid_A1
    assert b_objs[0].references["a"].objects[0].references is None
    assert b_objs[0].references["a"].objects[1].collection == A.name
    assert b_objs[0].references["a"].objects[1].properties["name"] == "A2"
    assert b_objs[0].references["a"].objects[1].uuid == uuid_A2
    assert b_objs[0].references["a"].objects[1].references is None

    dummy_c = collection_factory(
        name="C",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            Property(name="Age", data_type=DataType.INT),
        ],
        references=[
            ReferenceProperty(name="b", target_collection=B.name),
        ],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    C = collection_factory_get(dummy_c.name, CProps)
    C.data.insert(properties={"name": "find me"}, references={"b": uuid_B})

    if level == "col-col":
        c_objs = (
            collection_factory_get(C.name, CProps, CRefs)
            .query.bm25(query="find", include_vector=True)
            .objects
        )
    elif level == "col-query":
        c_objs = (
            collection_factory_get(C.name, CProps)
            .query.bm25(
                query="find",
                include_vector=True,
                return_references=CRefs,
            )
            .objects
        )
    elif level == "query-col":
        c_objs = (
            collection_factory_get(C.name, data_model_refs=CRefs)
            .query.bm25(
                query="find",
                include_vector=True,
                return_properties=CProps,
            )
            .objects
        )
    else:
        c_objs = (
            collection_factory_get(C.name)
            .query.bm25(
                query="find",
                include_vector=True,
                return_properties=CProps,
                return_references=CRefs,
            )
            .objects
        )
    assert c_objs[0].collection == C.name
    assert (
        c_objs[0].properties["name"] == "find me"
    )  # happy path (in type and in return_properties)
    assert c_objs[0].uuid is not None
    assert "default" in c_objs[0].vector
    assert (
        c_objs[0].properties.get("not_specified") is None
    )  # type is str but instance is None (in type but not in return_properties)
    assert c_objs[0].references["b"].objects[0].collection == B.name
    assert c_objs[0].references["b"].objects[0].properties["name"] == "B"
    assert c_objs[0].references["b"].objects[0].uuid == uuid_B
    assert "default" not in c_objs[0].references["b"].objects[0].vector
    assert c_objs[0].references["b"].objects[0].references["a"].objects[0].collection == A.name
    assert (
        c_objs[0].references["b"].objects[0].references["a"].objects[0].properties["name"] == "A1"
    )
    assert c_objs[0].references["b"].objects[0].references["a"].objects[0].uuid == uuid_A1
    assert (
        c_objs[0].references["b"].objects[0].references["a"].objects[0].metadata.creation_time
        is not None
    )
    assert "default" in c_objs[0].references["b"].objects[0].references["a"].objects[0].vector
    assert c_objs[0].references["b"].objects[0].references["a"].objects[1].collection == A.name
    assert (
        c_objs[0].references["b"].objects[0].references["a"].objects[1].properties["name"] == "A2"
    )
    assert c_objs[0].references["b"].objects[0].references["a"].objects[1].uuid == uuid_A2
    assert (
        c_objs[0].references["b"].objects[0].references["a"].objects[1].metadata.creation_time
        is not None
    )
    assert "default" in c_objs[0].references["b"].objects[0].references["a"].objects[1].vector


def test_multi_references_grpc(collection_factory: CollectionFactory) -> None:
    A = collection_factory(
        name="A",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
    )
    uuid_A = A.data.insert(properties={"Name": "A"})

    B = collection_factory(
        name="B",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid_B = B.data.insert({"Name": "B"})

    C = collection_factory(
        name="C",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        references=[
            ReferenceProperty.MultiTarget(name="ref", target_collections=[A.name, B.name]),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    C.data.insert(
        {
            "Name": "first",
        },
        references={
            "ref": ReferenceToMulti(uuids=uuid_A, target_collection=A.name),
        },
    )
    C.data.insert(
        {
            "Name": "second",
        },
        references={
            "ref": ReferenceToMulti(uuids=uuid_B, target_collection=B.name),
        },
    )

    objects = C.query.bm25(
        query="first",
        return_properties="name",
        return_references=QueryReference.MultiTarget(
            link_on="ref",
            target_collection=A.name,
            return_properties=["name"],
            return_metadata=MetadataQuery(last_update_time=True),
        ),
    ).objects
    assert objects[0].collection == C.name
    assert objects[0].properties["name"] == "first"
    assert len(objects[0].references["ref"].objects) == 1
    assert objects[0].references["ref"].objects[0].collection == A.name
    assert objects[0].references["ref"].objects[0].properties["name"] == "A"
    assert objects[0].references["ref"].objects[0].metadata.last_update_time is not None

    objects = C.query.bm25(
        query="second",
        return_properties="name",
        return_references=QueryReference.MultiTarget(
            link_on="ref",
            target_collection=B.name,
            return_properties=[
                "name",
            ],
            return_metadata=MetadataQuery(last_update_time=True),
        ),
    ).objects
    assert objects[0].collection == C.name
    assert objects[0].properties["name"] == "second"
    assert len(objects[0].references["ref"].objects) == 1
    assert objects[0].references["ref"].objects[0].collection == B.name
    assert objects[0].references["ref"].objects[0].properties["name"] == "B"
    assert objects[0].references["ref"].objects[0].metadata.last_update_time is not None


def test_multi_references_grpc_with_generics(collection_factory: CollectionFactory) -> None:
    A = collection_factory(
        name="A",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
    )
    uuid_A = A.data.insert(properties={"Name": "A"})

    B = collection_factory(
        name="B",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid_B = B.data.insert({"Name": "B"})

    C = collection_factory(
        name="C",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        references=[
            ReferenceProperty.MultiTarget(name="ref", target_collections=[A.name, B.name]),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    C.data.insert(
        {
            "Name": "first",
        },
        references={
            "ref": ReferenceToMulti(uuids=uuid_A, target_collection=A.name),
        },
    )
    C.data.insert(
        {
            "Name": "second",
        },
        references={
            "ref": ReferenceToMulti(uuids=uuid_B, target_collection=B.name),
        },
    )

    class AProps(TypedDict):
        name: str

    class BProps(TypedDict):
        name: str

    class CProps(TypedDict):
        name: str

    class CRefsA(TypedDict):
        ref: Annotated[
            CrossReference[AProps, None],
            CrossReferenceAnnotation(
                metadata=MetadataQuery(last_update_time=True), target_collection=A.name
            ),
        ]

    class CRefsB(TypedDict):
        ref: Annotated[
            CrossReference[BProps, None],
            CrossReferenceAnnotation(
                metadata=MetadataQuery(last_update_time=True), target_collection=B.name
            ),
        ]

    objects = C.query.bm25(
        query="first",
        return_properties=CProps,
        return_references=CRefsA,
    ).objects
    assert objects[0].collection == C.name
    assert objects[0].properties["name"] == "first"
    assert len(objects[0].references["ref"].objects) == 1
    assert objects[0].references["ref"].objects[0].collection == A.name
    assert objects[0].references["ref"].objects[0].properties["name"] == "A"
    assert objects[0].references["ref"].objects[0].metadata.last_update_time is not None

    objects = C.query.bm25(
        query="second",
        return_properties=CProps,
        return_references=CRefsB,
    ).objects
    assert objects[0].collection == C.name
    assert objects[0].properties["name"] == "second"
    assert len(objects[0].references["ref"].objects) == 1
    assert objects[0].references["ref"].objects[0].collection == B.name
    assert objects[0].references["ref"].objects[0].properties["name"] == "B"
    assert objects[0].references["ref"].objects[0].metadata.last_update_time is not None


def test_references_batch(collection_factory: CollectionFactory) -> None:
    ref_collection = collection_factory(
        name="To",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="number", data_type=DataType.INT)],
    )
    num_objects = 10

    uuids_to = list(
        ref_collection.data.insert_many(
            [DataObject(properties={"number": i}) for i in range(num_objects)]
        ).uuids.values()
    )
    collection = collection_factory(
        name="From",
        properties=[
            Property(name="num", data_type=DataType.INT),
        ],
        references=[ReferenceProperty(name="ref", target_collection=ref_collection.name)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuids_from = list(
        collection.data.insert_many(
            [DataObject(properties={"num": i}) for i in range(num_objects)]
        ).uuids.values()
    )

    # use both ways of adding batch-references in two calls to preserve order:
    # - single points to an object with the same value as property
    # - multi always points to the first 3 objects
    batch_return = collection.data.reference_add_many(
        [
            DataReference(
                from_property="ref",
                from_uuid=uuids_from[i],
                to_uuid=uuids_to[i],
            )
            for i in range(num_objects)
        ]
    )
    assert batch_return.has_errors is False

    batch_return = collection.data.reference_add_many(
        [
            DataReference(
                from_property="ref",
                from_uuid=uuids_from[i],
                to_uuid=[uuids_to[j] for j in range(3)],
            )
            for i in range(num_objects)
        ]
    )
    assert batch_return.has_errors is False

    objects = collection.query.fetch_objects(
        return_properties=["num"],
        return_references=[QueryReference(link_on="ref")],
    ).objects

    for obj in objects:
        assert obj.properties["num"] == obj.references["ref"].objects[0].properties["number"]
        assert obj.references["ref"].objects[0].uuid in uuids_to
        assert len(obj.references["ref"].objects) == 4
        refs = [obj.references["ref"].objects[j + 1].properties["number"] for j in range(3)]
        refs.sort()
        assert [0, 1, 2] == refs


def test_batch_reference_multi_taret(collection_factory: CollectionFactory) -> None:
    to_collection = collection_factory(
        name="To",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="number", data_type=DataType.INT)],
    )
    from_collection = collection_factory(
        name="From",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="num", data_type=DataType.INT)],
    )
    from_collection.config.add_reference(
        ReferenceProperty.MultiTarget(
            name="ref", target_collections=[to_collection.name, from_collection.name]
        )
    )

    num_objects = 5

    uuids_to = list(
        to_collection.data.insert_many(
            [DataObject(properties={"number": i}) for i in range(num_objects)]
        ).uuids.values()
    )
    uuids_from = list(
        from_collection.data.insert_many(
            [DataObject(properties={"num": i}) for i in range(num_objects)]
        ).uuids.values()
    )

    # add to to_collection
    batch_return = from_collection.data.reference_add_many(
        [
            DataReference.MultiTarget(
                from_property="ref",
                from_uuid=uuids_from[i],
                to_uuid=uuids_to[i],
                target_collection=to_collection.name,
            )
            for i in range(num_objects)
        ]
    )
    assert batch_return.has_errors is False

    # add to from_collection
    batch_return = from_collection.data.reference_add_many(
        [
            DataReference.MultiTarget(
                from_property="ref",
                from_uuid=uuids_from[i],
                to_uuid=uuids_from[i],
                target_collection=from_collection.name,
            )
            for i in range(num_objects)
        ]
    )
    assert batch_return.has_errors is False

    objects_with_to_ref = from_collection.query.fetch_objects(
        return_properties=["num"],
        return_references=[
            QueryReference.MultiTarget(link_on="ref", target_collection=to_collection.name)
        ],
    ).objects
    for obj in objects_with_to_ref:
        assert obj.properties["num"] == obj.references["ref"].objects[0].properties["number"]

    objects_with_from_ref = from_collection.query.fetch_objects(
        return_properties=["num"],
        return_references=[
            QueryReference.MultiTarget(link_on="ref", target_collection=from_collection.name)
        ],
    ).objects
    for obj in objects_with_from_ref:
        assert obj.properties["num"] == obj.references["ref"].objects[0].properties["num"]


def test_insert_many_with_refs(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.config.add_reference(
        ReferenceProperty(name="self", target_collection=collection.name)
    )

    uuid1 = collection.data.insert({"name": "A"})
    uuid2 = collection.data.insert({"name": "B"})

    batch_return = collection.data.insert_many(
        [
            DataObject(
                properties={"name": "C"},
                references={"self": uuid1},
            ),
            DataObject(
                properties={"name": "D"},
                references={"self": [uuid1, uuid2]},
            ),
            DataObject(
                properties={"name": "E"},
                references={"self": uuid1},
            ),
            DataObject(
                properties={"name": "F"},
                references={"self": [uuid1, uuid2]},
            ),
        ]
    )
    assert batch_return.has_errors is False

    for obj in collection.query.fetch_objects(
        return_properties=["name"], return_references=QueryReference(link_on="self")
    ).objects:
        if obj.properties["name"] in ["A", "B"]:
            assert obj.references == {}
        else:
            assert obj.references is not None
            if obj.properties["name"] == "C":
                assert obj.references["self"].objects[0].uuid == uuid1
            elif obj.properties["name"] == "D":
                assert obj.references["self"].objects[0].uuid == uuid1
                assert obj.references["self"].objects[1].uuid == uuid2
            elif obj.properties["name"] == "E":
                assert obj.references["self"].objects[0].uuid == uuid1
            elif obj.properties["name"] == "F":
                assert obj.references["self"].objects[0].uuid == uuid1
                assert obj.references["self"].objects[1].uuid == uuid2


def test_references_batch_with_errors(collection_factory: CollectionFactory) -> None:
    to = collection_factory(
        name="To",
        vectorizer_config=Configure.Vectorizer.none(),
    )

    collection = collection_factory(
        name="From",
        properties=[
            Property(name="num", data_type=DataType.INT),
        ],
        references=[ReferenceProperty(name="ref", target_collection=to.name)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    batch_return = collection.data.reference_add_many(
        [DataReference(from_property="doesNotExist", from_uuid=uuid.uuid4(), to_uuid=uuid.uuid4())],
    )
    assert batch_return.has_errors is True
    assert 0 in batch_return.errors


# commented out due to mypy failures since it is stale code
# @pytest.mark.skip(reason="string syntax has been temporarily removed from the API")
# def test_references_with_string_syntax(client: weaviate.WeaviateClient):
#     name1 = "TestReferencesWithStringSyntaxA"
#     name2 = "TestReferencesWithStringSyntaxB"
#     client.collections.delete(name1)
#     client.collections.delete(name2)

#     client.collections.create(
#         name=name1,
#         vectorizer_config=Configure.Vectorizer.none(),
#         properties=[
#             Property(name="Name", data_type=DataType.TEXT),
#             Property(name="Age", data_type=DataType.INT),
#             Property(name="Weird__Name", data_type=DataType.INT),
#         ],
#     )

#     uuid_A = client.collections.get(name1).data.insert(
#         properties={"Name": "A", "Age": 1, "Weird__Name": 2}
#     )

#     client.collections.get(name1).query.fetch_object_by_id(uuid_A)

#     client.collections.create(
#         name=name2,
#         properties=[
#             Property(name="Name", data_type=DataType.TEXT),
#         ],
#         references=[ReferenceProperty(name="ref", target_collection=name1)],
#         vectorizer_config=Configure.Vectorizer.none(),
#     )

#     client.collections.get(name2).data.insert(
#         {"Name": "B"}, references={"ref": reference_to_no_warning(uuids=uuid_A)}
#     )

#     objects = (
#         client.collections.get(name2)
#         .query.bm25(
#             query="B",
#             return_properties=[
#                 "name",
#                 "__ref__properties__Name",
#                 "__ref__properties__Age",
#                 "__ref__properties__Weird__Name",
#                 "__ref__metadata__last_update_time_unix",
#             ],
#         )
#         .objects
#     )

#     assert objects[0].properties["name"] == "B"
#     assert objects[0].references["ref"].objects[0].properties["name"] == "A"
#     assert objects[0].references["ref"].objects[0].properties["age"] == 1
#     assert objects[0].references["ref"].objects[0].properties["weird__Name"] == 2
#     assert objects[0].references["ref"].objects[0].uuid == uuid_A
#     assert objects[0].references["ref"].objects[0].metadata.last_update_time_unix is not None


def test_object_without_references(collection_factory: CollectionFactory) -> None:
    to = collection_factory(name="To", vectorizer_config=Configure.Vectorizer.none())

    source = collection_factory(
        name="From",
        references=[
            ReferenceProperty(name="ref_partial", target_collection=to.name),
            ReferenceProperty(name="ref_full", target_collection=to.name),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    uuid_to = to.data.insert(properties={})

    uuid_from1 = source.data.insert(
        references={"ref_partial": uuid_to, "ref_full": uuid_to},
        properties={},
    )
    uuid_from2 = source.data.insert(references={"ref_full": uuid_to}, properties={})

    obj1 = source.query.fetch_object_by_id(
        uuid_from2,
        return_references=[
            QueryReference(link_on="ref_full"),
            QueryReference(link_on="ref_partial"),
        ],
    )
    assert "ref_full" in obj1.references and "ref_partial" not in obj1.references
    assert obj1.collection == source.name

    obj2 = source.query.fetch_object_by_id(
        uuid_from1,
        return_references=[
            QueryReference(link_on="ref_full"),
            QueryReference(link_on="ref_partial"),
        ],
    )
    assert "ref_full" in obj2.references and "ref_partial" in obj2.references
    assert obj2.collection == source.name


def test_ref_case_sensitivity(collection_factory: CollectionFactory) -> None:
    to = collection_factory(name="To", vectorizer_config=Configure.Vectorizer.none())

    source = collection_factory(
        name="From",
        references=[
            ReferenceProperty(name="ref", target_collection=to.name),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    # added as upper-case UUID
    uuid_upper_str = "4E5CD755-4F43-44C5-B23C-0C7D6F6C21E6"
    to.data.insert(uuid=uuid_upper_str, properties={})

    # adding a ref as lower-case UUID should work
    from1 = source.data.insert(properties={}, references={"ref": uuid_upper_str.lower()})

    # try to add as upper-case UUID via different methods
    from2 = source.data.insert(properties={}, references={"ref": uuid_upper_str})
    from3 = source.data.insert(properties={})
    source.data.reference_add(from_uuid=from3, from_property="ref", to=uuid_upper_str)

    from4 = source.data.insert(properties={})
    source.data.reference_add_many(
        [DataReference(from_uuid=from4, from_property="ref", to_uuid=uuid_upper_str)]
    )

    from5 = source.data.insert_many(
        [DataObject(properties={}, references={"ref": uuid_upper_str})]
    ).uuids[0]

    for uid in [from1, from2, from3, from4, from5]:
        obj = source.query.fetch_object_by_id(
            uid, return_references=[QueryReference(link_on="ref")]
        )
        assert "ref" in obj.references


def test_empty_return_reference(collection_factory: CollectionFactory) -> None:
    to = collection_factory(name="To", vectorizer_config=Configure.Vectorizer.none())
    source = collection_factory(
        name="From",
        references=[
            ReferenceProperty(name="ref", target_collection=to.name),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid_source = source.data.insert(properties={})
    obj = source.query.fetch_object_by_id(
        uuid_source, return_references=[QueryReference(link_on="ref")]
    )
    assert obj.references == {}


@pytest.mark.parametrize(
    "to_uuid",
    [TO_UUID, str(TO_UUID), [TO_UUID], [str(TO_UUID)]],
)
def test_refs_different_input_insert(
    collection_factory: CollectionFactory, to_uuid: ReferenceInput
) -> None:
    to = collection_factory(name="To", vectorizer_config=Configure.Vectorizer.none())
    to.data.insert(properties={}, uuid=TO_UUID)

    source = collection_factory(
        name="From",
        references=[
            ReferenceProperty(name="ref", target_collection=to.name),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    from_uuid = source.data.insert(properties={}, references={"ref": to_uuid})
    obj = source.query.fetch_object_by_id(
        from_uuid, return_references=[QueryReference(link_on="ref")]
    )
    assert obj.references["ref"].objects[0].uuid == TO_UUID


@pytest.mark.parametrize(
    "to_uuid",
    [TO_UUID, str(TO_UUID), [TO_UUID], [str(TO_UUID)]],
)
def test_refs_different_input_insert_many(
    collection_factory: CollectionFactory, to_uuid: ReferenceInput
) -> None:
    to = collection_factory(name="To", vectorizer_config=Configure.Vectorizer.none())
    to.data.insert(properties={}, uuid=TO_UUID)

    source = collection_factory(
        name="From",
        references=[
            ReferenceProperty(name="ref", target_collection=to.name),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    source.config.add_reference(
        ReferenceProperty.MultiTarget(name="multi", target_collections=[to.name, source.name])
    )

    from_uuid = source.data.insert_many([DataObject(properties={}, references={"ref": to_uuid})])
    assert not from_uuid.has_errors
    assert len(from_uuid.uuids) == 1
    obj = source.query.fetch_object_by_id(
        from_uuid.uuids[0], return_references=[QueryReference(link_on="ref")]
    )
    assert obj.references["ref"].objects[0].uuid == TO_UUID

    from_uuid4 = source.data.insert_many(
        [
            DataObject(
                properties={},
                references={"multi": ReferenceToMulti(uuids=TO_UUID, target_collection=to.name)},
            )
        ]
    )
    assert not from_uuid4.has_errors
    assert len(from_uuid4.uuids) == 1
    obj = source.query.fetch_object_by_id(
        from_uuid4.uuids[0],
        return_references=[QueryReference.MultiTarget(link_on="multi", target_collection=to.name)],
    )
    assert obj.references["multi"].objects[0].uuid == TO_UUID


@pytest.mark.parametrize("to_uuid", [TO_UUID, str(TO_UUID)])
def test_refs_different_reference_add(collection_factory: CollectionFactory, to_uuid: str) -> None:
    to = collection_factory(name="To", vectorizer_config=Configure.Vectorizer.none())
    to.data.insert(properties={}, uuid=TO_UUID)

    source = collection_factory(
        name="From",
        references=[
            ReferenceProperty(name="ref", target_collection=to.name),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    from_uuid = source.data.insert(properties={})

    source.data.reference_add(from_property="ref", from_uuid=from_uuid, to=to_uuid)

    obj = source.query.fetch_object_by_id(
        from_uuid, return_references=[QueryReference(link_on="ref")]
    )
    assert obj.references["ref"].objects[0].uuid == TO_UUID


@pytest.mark.parametrize("to_uuid", [TO_UUID, str(TO_UUID), [TO_UUID], [str(TO_UUID)]])
def test_refs_different_reference_add_many(
    collection_factory: CollectionFactory, to_uuid: UUID
) -> None:
    to = collection_factory(name="To", vectorizer_config=Configure.Vectorizer.none())
    to.data.insert(properties={}, uuid=TO_UUID)
    to.data.insert(properties={}, uuid=TO_UUID2)

    source = collection_factory(
        name="From",
        references=[
            ReferenceProperty(name="ref", target_collection=to.name),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    from_uuid = source.data.insert(properties={})

    source.data.reference_add_many(
        [DataReference(from_property="ref", from_uuid=from_uuid, to_uuid=to_uuid)]
    )

    obj = source.query.fetch_object_by_id(
        from_uuid, return_references=[QueryReference(link_on="ref")]
    )
    assert obj.references["ref"].objects[0].uuid == TO_UUID


@pytest.mark.parametrize(
    "to_uuid",
    [TO_UUID2, str(TO_UUID2), [TO_UUID2], [str(TO_UUID2)]],
)
def test_refs_different_reference_replace(
    collection_factory: CollectionFactory, to_uuid: ReferenceInput
) -> None:
    to = collection_factory(name="To", vectorizer_config=Configure.Vectorizer.none())
    to.data.insert(properties={}, uuid=TO_UUID)
    to.data.insert(properties={}, uuid=TO_UUID2)

    source = collection_factory(
        name="From",
        references=[
            ReferenceProperty(name="ref", target_collection=to.name),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    from_uuid = source.data.insert(properties={})
    source.data.reference_add(from_property="ref", from_uuid=from_uuid, to=TO_UUID)
    obj = source.query.fetch_object_by_id(
        from_uuid, return_references=[QueryReference(link_on="ref")]
    )
    assert obj.references["ref"].objects[0].uuid == TO_UUID

    source.data.reference_replace(from_property="ref", from_uuid=from_uuid, to=to_uuid)
    obj = source.query.fetch_object_by_id(
        from_uuid, return_references=[QueryReference(link_on="ref")]
    )
    assert obj.references["ref"].objects[0].uuid == TO_UUID2


def test_bad_generic_return_references(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
    )

    class SomeGeneric(TypedDict):
        field: int

    uuid = collection.data.insert(properties={"Name": "A"})
    with pytest.raises(WeaviateInvalidInputError):
        collection.query.fetch_object_by_id(
            uuid,
            return_references=SomeGeneric,
        )

    class OtherGeneric(TypedDict):
        field: Annotated[
            int,
            CrossReferenceAnnotation(metadata=MetadataQuery(creation_time=True)),
        ]

    with pytest.raises(WeaviateInvalidInputError):
        collection.query.fetch_object_by_id(
            uuid,
            return_references=SomeGeneric,
        )


def test_generic_type_hint_return_references(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        data_model_refs=Dict[str, CrossReference[Dict[str, str], None]],
    )
    collection.config.add_reference(
        ReferenceProperty(name="self", target_collection=collection.name)
    )

    uuid1 = collection.data.insert(properties={"Name": "A"})
    uuid2 = collection.data.insert(properties={"Name": "B"}, references={"self": uuid1})
    obj = collection.query.fetch_object_by_id(
        uuid2,
        return_references=QueryReference(
            link_on="self",
        ),
    )
    assert obj.properties == {"name": "B"}
    assert obj.references["self"].objects[0].uuid == uuid1
    assert obj.references["self"].objects[0].properties == {"name": "A"}
