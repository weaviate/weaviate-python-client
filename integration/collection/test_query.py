import datetime
import sys
from typing import List, Optional, TypedDict, Union

import pytest as pytest
import uuid

from weaviate.collection.classes.grpc import Sort

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from integration.constants import WEAVIATE_LOGO_OLD_ENCODED, WEAVIATE_LOGO_NEW_ENCODED
from weaviate.collection import Collection
from weaviate.collection.classes.config import (
    ConfigFactory,
    Property,
    DataType,
    ReferenceProperty,
    ReferencePropertyMultiTarget,
    VectorizerFactory,
)
from weaviate.collection.classes.data import (
    DataObject,
)
from weaviate.collection.classes.internal import ReferenceFactory
from weaviate.collection.classes.tenants import Tenant
from weaviate.exceptions import WeaviateGRPCException
from weaviate.collection.grpc import HybridFusion, LinkTo, LinkToMultiTarget, MetadataQuery, Move
from weaviate.weaviate_types import UUID

UUID1 = uuid.uuid4()


@pytest.mark.parametrize("fusion_type", [HybridFusion.RANKED, HybridFusion.RELATIVE_SCORE])
def test_search_hybrid(collection_basic: Collection, fusion_type):
    collection = collection_basic.create(
        name="Testing",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.text2vec_contextionary(),
    )
    collection.data.insert({"Name": "some name"}, uuid.uuid4())
    collection.data.insert({"Name": "other word"}, uuid.uuid4())
    res = collection.query.hybrid(alpha=0, query="name", fusion_type=fusion_type)
    assert len(res) == 1
    collection_basic.delete("Testing")


@pytest.mark.parametrize("limit", [1, 5])
def test_search_limit(collection_basic: Collection, limit):
    collection = collection_basic.create(
        name="TestLimit",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )
    for i in range(5):
        collection.data.insert({"Name": str(i)})

    assert len(collection.query.get(limit=limit)) == limit

    collection_basic.delete("TestLimit")


@pytest.mark.parametrize("offset", [0, 1, 5])
def test_search_offset(collection_basic: Collection, offset):
    collection = collection_basic.create(
        name="TestOffset",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )

    nr_objects = 5
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.get(offset=offset)
    assert len(objects) == nr_objects - offset

    collection_basic.delete("TestOffset")


def test_search_after(collection_basic: Collection):
    collection = collection_basic.create(
        name="TestOffset",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )

    nr_objects = 10
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.get(return_metadata=MetadataQuery(uuid=True))
    for i, obj in enumerate(objects):
        objects_after = collection.query.get(after=obj.metadata.uuid)
        assert len(objects_after) == nr_objects - 1 - i

    collection_basic.delete("TestOffset")


def test_auto_limit(collection_basic: Collection):
    collection = collection_basic.create(
        name="TestAutoLimit",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )
    for _ in range(4):
        collection.data.insert({"Name": "rain rain"})
    for _ in range(4):
        collection.data.insert({"Name": "rain"})
    for _ in range(4):
        collection.data.insert({"Name": ""})

    # match all objects with rain
    objects = collection.query.bm25(query="rain", auto_limit=0)
    assert len(objects) == 2 * 4
    objects = collection.query.hybrid(
        query="rain", auto_limit=0, alpha=0, fusion_type=HybridFusion.RELATIVE_SCORE
    )
    assert len(objects) == 2 * 4

    # match only objects with two rains
    objects = collection.query.bm25(query="rain", auto_limit=1)
    assert len(objects) == 1 * 4
    objects = collection.query.hybrid(
        query="rain", auto_limit=1, alpha=0, fusion_type=HybridFusion.RELATIVE_SCORE
    )
    assert len(objects) == 1 * 4

    collection_basic.delete("TestAutoLimit")


def test_query_properties(collection_basic: Collection):
    collection = collection_basic.create(
        name="TestQueryProperties",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            Property(name="Age", data_type=DataType.INT),
        ],
        vectorizer_config=VectorizerFactory.none(),
    )
    collection.data.insert({"Name": "rain", "Age": 1})
    collection.data.insert({"Name": "sun", "Age": 2})
    collection.data.insert({"Name": "cloud", "Age": 3})
    collection.data.insert({"Name": "snow", "Age": 4})
    collection.data.insert({"Name": "hail", "Age": 5})

    objects = collection.query.bm25(query="rain", query_properties=["name"])
    assert len(objects) == 1
    assert objects[0].properties["age"] == 1

    objects = collection.query.bm25(query="sleet", query_properties=["name"])
    assert len(objects) == 0

    objects = collection.query.hybrid(query="cloud", query_properties=["name"], alpha=0)
    assert len(objects) == 1
    assert objects[0].properties["age"] == 3

    objects = collection.query.hybrid(query="sleet", query_properties=["name"], alpha=0)
    assert len(objects) == 0

    collection_basic.delete("TestQueryProperties")


def test_near_vector(collection_basic: Collection):
    collection = collection_basic.create(
        name="TestNearVector",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.text2vec_contextionary(),
    )
    uuid_banana = collection.data.insert({"Name": "Banana"})
    collection.data.insert({"Name": "Fruit"})
    collection.data.insert({"Name": "car"})
    collection.data.insert({"Name": "Mountain"})

    banana = collection.data.get_by_id(uuid_banana, include_vector=True)

    full_objects = collection.query.near_vector(
        banana.metadata.vector, return_metadata=MetadataQuery(distance=True, certainty=True)
    )
    assert len(full_objects) == 4

    objects_distance = collection.query.near_vector(
        banana.metadata.vector, distance=full_objects[2].metadata.distance
    )
    assert len(objects_distance) == 3

    objects_distance = collection.query.near_vector(
        banana.metadata.vector, certainty=full_objects[2].metadata.certainty
    )
    assert len(objects_distance) == 3

    collection_basic.delete("TestNearVector")


def test_near_object(collection_basic: Collection):
    collection = collection_basic.create(
        name="TestNearObject",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.text2vec_contextionary(),
    )
    uuid_banana = collection.data.insert({"Name": "Banana"})
    collection.data.insert({"Name": "Fruit"})
    collection.data.insert({"Name": "car"})
    collection.data.insert({"Name": "Mountain"})

    full_objects = collection.query.near_object(
        uuid_banana, return_metadata=MetadataQuery(distance=True, certainty=True)
    )
    assert len(full_objects) == 4

    objects_distance = collection.query.near_object(
        uuid_banana, distance=full_objects[2].metadata.distance
    )
    assert len(objects_distance) == 3

    objects_certainty = collection.query.near_object(
        uuid_banana, certainty=full_objects[2].metadata.certainty
    )
    assert len(objects_certainty) == 3

    collection_basic.delete("TestNearObject")


def test_mono_references_grpc(collection_basic: Collection):
    A = collection_basic.create(
        name="A",
        vectorizer_config=VectorizerFactory.none(),
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
    )
    uuid_A1 = A.data.insert(properties={"Name": "A1"})
    uuid_A2 = A.data.insert(properties={"Name": "A2"})

    objects = A.query.bm25(query="A1", return_properties="name")
    assert objects[0].properties["name"] == "A1"

    B = collection_basic.create(
        name="B",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferenceProperty(name="ref", target_collection="A"),
        ],
        vectorizer_config=VectorizerFactory.none(),
    )
    uuid_B = B.data.insert({"Name": "B", "ref": ReferenceFactory.to(uuids=uuid_A1)})
    B.data.reference_add(
        from_uuid=uuid_B, from_property="ref", ref=ReferenceFactory.to(uuids=uuid_A2)
    )

    objects = B.query.bm25(
        query="B",
        return_properties=LinkTo(
            link_on="ref",
            return_properties=["name"],
        ),
    )
    assert objects[0].properties["ref"].objects[0].properties["name"] == "A1"
    assert objects[0].properties["ref"].objects[1].properties["name"] == "A2"

    objects = B.query.bm25(
        query="B",
        return_properties=[
            LinkTo(
                link_on="ref",
                return_properties=["name"],
                return_metadata=MetadataQuery(uuid=True),
            )
        ],
    )
    assert objects[0].properties["ref"].objects[0].properties["name"] == "A1"
    assert objects[0].properties["ref"].objects[0].metadata.uuid == uuid_A1
    assert objects[0].properties["ref"].objects[1].properties["name"] == "A2"
    assert objects[0].properties["ref"].objects[1].metadata.uuid == uuid_A2

    C = collection_basic.create(
        name="C",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferenceProperty(name="ref", target_collection="B"),
        ],
        vectorizer_config=VectorizerFactory.none(),
    )
    C.data.insert({"Name": "find me", "ref": ReferenceFactory.to(uuids=uuid_B)})

    objects = C.query.bm25(
        query="find",
        return_properties=[
            "name",
            LinkTo(
                link_on="ref",
                return_properties=[
                    "name",
                    LinkTo(
                        link_on="ref",
                        return_properties=["name"],
                        return_metadata=MetadataQuery(uuid=True),
                    ),
                ],
                return_metadata=MetadataQuery(uuid=True, last_update_time_unix=True),
            ),
        ],
    )
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


def test_mono_references_grpc_typed_dicts(collection_basic: Collection):
    collection_basic.delete("ATypedDicts")
    collection_basic.delete("BTypedDicts")
    collection_basic.delete("CTypedDicts")

    class AProps(TypedDict):
        name: str

    class BProps(TypedDict):
        name: str
        ref: Annotated[ReferenceFactory[AProps], MetadataQuery(uuid=True)]

    class CProps(TypedDict):
        name: str
        ref: Annotated[ReferenceFactory[BProps], MetadataQuery(uuid=True)]

    collection_basic.create(
        name="ATypedDicts",
        vectorizer_config=VectorizerFactory.none(),
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
    )
    A = collection_basic.get("ATypedDicts", AProps)
    uuid_A1 = A.data.insert(AProps(name="A1"))
    uuid_A2 = A.data.insert(AProps(name="A2"))

    B = collection_basic.create(
        name="BTypedDicts",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferenceProperty(name="ref", target_collection="ATypedDicts"),
        ],
        vectorizer_config=VectorizerFactory.none(),
    )
    B = collection_basic.get("BTypedDicts", BProps)
    uuid_B = B.data.insert(
        properties=BProps(name="B", ref=ReferenceFactory[AProps].to(uuids=uuid_A1))
    )
    B.data.reference_add(
        from_uuid=uuid_B, from_property="ref", ref=ReferenceFactory[AProps].to(uuids=uuid_A2)
    )

    collection_basic.create(
        name="CTypedDicts",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            Property(name="Age", data_type=DataType.INT),
            ReferenceProperty(name="ref", target_collection="BTypedDicts"),
        ],
        vectorizer_config=VectorizerFactory.none(),
    )
    C = collection_basic.get("CTypedDicts", CProps)
    C.data.insert(properties=CProps(name="find me", ref=ReferenceFactory[BProps].to(uuids=uuid_B)))

    objects = collection_basic.get("CTypedDicts").query.bm25(
        query="find",
        return_properties=CProps,
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


def test_multi_references_grpc(collection_basic: Collection):
    collection_basic.delete("A")
    collection_basic.delete("B")
    collection_basic.delete("C")

    A = collection_basic.create(
        name="A",
        vectorizer_config=VectorizerFactory.none(),
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
    )
    uuid_A = A.data.insert(properties={"Name": "A"})

    B = collection_basic.create(
        name="B",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
        vectorizer_config=VectorizerFactory.none(),
    )
    uuid_B = B.data.insert({"Name": "B"})

    C = collection_basic.create(
        name="C",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferencePropertyMultiTarget(name="ref", target_collections=["A", "B"]),
        ],
        vectorizer_config=VectorizerFactory.none(),
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
            LinkToMultiTarget(
                link_on="ref",
                target_collection="A",
                return_properties=["name"],
                return_metadata=MetadataQuery(uuid=True, last_update_time_unix=True),
            ),
        ],
    )
    assert objects[0].properties["name"] == "first"
    assert len(objects[0].properties["ref"].objects) == 1
    assert objects[0].properties["ref"].objects[0].properties["name"] == "A"

    objects = C.query.bm25(
        query="second",
        return_properties=[
            "name",
            LinkToMultiTarget(
                link_on="ref",
                target_collection="B",
                return_properties=[
                    "name",
                ],
                return_metadata=MetadataQuery(uuid=True, last_update_time_unix=True),
            ),
        ],
    )
    assert objects[0].properties["name"] == "second"
    assert len(objects[0].properties["ref"].objects) == 1
    assert objects[0].properties["ref"].objects[0].properties["name"] == "B"

    collection_basic.delete("A")
    collection_basic.delete("B")
    collection_basic.delete("C")


def test_multi_searches(collection_basic: Collection):
    collection_basic.delete("TestMultiSearches")
    collection = collection_basic.create(
        name="TestMultiSearches",
        properties=[Property(name="name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )

    collection.data.insert(properties={"name": "word"})
    collection.data.insert(properties={"name": "other"})

    objects = collection.query.bm25(
        query="word",
        return_properties=["name"],
        return_metadata=MetadataQuery(last_update_time_unix=True),
    )
    assert "name" in objects[0].properties
    assert objects[0].metadata.last_update_time_unix is not None

    objects = collection.query.bm25(query="other", return_metadata=MetadataQuery(uuid=True))
    assert "name" not in objects[0].properties
    assert objects[0].metadata.uuid is not None
    assert objects[0].metadata.last_update_time_unix is None


def test_search_with_tenant(collection_basic: Collection):
    collection_basic.delete("TestTenantSearch")
    collection = collection_basic.create(
        name="TestTenantSearch",
        vectorizer_config=VectorizerFactory.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
        multi_tenancy_config=ConfigFactory.multi_tenancy(enabled=True),
    )

    collection.tenants.add([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")
    uuid1 = tenant1.data.insert({"name": "some name"})
    objects1 = tenant1.query.bm25(query="some", return_metadata=MetadataQuery(uuid=True))
    assert len(objects1) == 1
    assert objects1[0].metadata.uuid == uuid1

    objects2 = tenant2.query.bm25(query="some", return_metadata=MetadataQuery(uuid=True))
    assert len(objects2) == 0


def test_empty_search_returns_everything(collection_basic: Collection):
    collection = collection_basic.create(
        name="TestReturnEverything",
        vectorizer_config=VectorizerFactory.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
    )

    collection.data.insert(properties={"name": "word"})

    objects = collection.query.bm25(query="word")
    assert "name" in objects[0].properties
    assert objects[0].properties["name"] == "word"
    assert objects[0].metadata.uuid is not None
    assert objects[0].metadata.score is not None
    assert objects[0].metadata.last_update_time_unix is not None
    assert objects[0].metadata.creation_time_unix is not None

    collection_basic.delete("TestReturnEverything")


def test_return_list_properties(collection_basic: Collection):
    name_small = "TestReturnList"
    collection = collection_basic.create(
        name=name_small,
        vectorizer_config=VectorizerFactory.none(),
        properties=[
            Property(name="ints", data_type=DataType.INT_ARRAY),
            Property(name="floats", data_type=DataType.NUMBER_ARRAY),
            Property(name="strings", data_type=DataType.TEXT_ARRAY),
            Property(name="bools", data_type=DataType.BOOL_ARRAY),
            Property(name="dates", data_type=DataType.DATE_ARRAY),
            Property(name="uuids", data_type=DataType.UUID_ARRAY),
        ],
    )
    data = {
        "ints": [1, 2, 3],
        "floats": [0.1, 0.4, 10.5],
        "strings": ["a", "list", "of", "strings"],
        "bools": [True, False, True],
        "dates": [
            datetime.datetime.strptime("2012-02-09", "%Y-%m-%d").replace(
                tzinfo=datetime.timezone.utc
            )
        ],
        "uuids": [uuid.uuid4(), uuid.uuid4()],
    }
    collection.data.insert(properties=data)
    objects = collection.query.get()
    assert len(objects) == 1

    # remove dates because of problems comparing dates
    dates_from_weaviate = objects[0].properties.pop("dates")
    dates2 = [datetime.datetime.fromisoformat(date) for date in dates_from_weaviate]
    dates = data.pop("dates")
    assert dates2 == dates

    # remove uuids because weaviate returns them as strings
    uuids_from_weaviate = objects[0].properties.pop("uuids")
    uuids2 = [uuid.UUID(uuids) for uuids in uuids_from_weaviate]
    uuids = data.pop("uuids")
    assert uuids2 == uuids

    assert objects[0].properties == data


@pytest.mark.parametrize("query", ["cake", ["cake"]])
@pytest.mark.parametrize("objects", [UUID1, str(UUID1), [UUID1], [str(UUID1)]])
@pytest.mark.parametrize("concepts", ["hiking", ["hiking"]])
def test_near_text(
    collection_basic: Collection,
    query: Union[str, List[str]],
    objects: Union[UUID, List[UUID]],
    concepts: Union[str, List[str]],
):
    name = "TestNearText"
    collection_basic.delete(name)
    collection = collection_basic.create(
        name=name,
        vectorizer_config=VectorizerFactory.text2vec_contextionary(),
        properties=[Property(name="value", data_type=DataType.TEXT)],
    )

    batch_return = collection.data.insert_many(
        [
            DataObject(properties={"value": "Apple"}, uuid=UUID1),
            DataObject(properties={"value": "Mountain climbing"}),
            DataObject(properties={"value": "apple cake"}),
            DataObject(properties={"value": "cake"}),
        ]
    )

    objs = collection.query.near_text(
        query=query,
        move_to=Move(force=1.0, objects=objects),
        move_away=Move(force=0.5, concepts=concepts),
        return_metadata=MetadataQuery(uuid=True),
        return_properties=["value"],
    )

    assert objs[0].metadata.uuid == batch_return.uuids[2]
    assert objs[0].properties["value"] == "apple cake"


def test_near_text_error(collection_basic: Collection):
    name = "TestNearTextError"
    collection_basic.delete(name)
    collection = collection_basic.create(
        name=name,
        vectorizer_config=VectorizerFactory.none(),
    )

    with pytest.raises(ValueError):
        collection.query.near_text(query="test", move_to=Move(force=1.0))


@pytest.mark.parametrize("distance,certainty", [(None, None), (10, None), (None, 0.1)])
def test_near_image(
    collection_basic: Collection, distance: Optional[float], certainty: Optional[float]
):
    name = "TestNearImage"
    collection_basic.delete(name)
    collection = collection_basic.create(
        name=name,
        vectorizer_config=VectorizerFactory.img2vec_neural(image_fields=["imageProp"]),
        properties=[
            Property(name="imageProp", data_type=DataType.BLOB),
        ],
    )

    uuid1 = collection.data.insert(properties={"imageProp": WEAVIATE_LOGO_OLD_ENCODED})
    collection.data.insert(properties={"imageProp": WEAVIATE_LOGO_NEW_ENCODED})

    objects = collection.query.near_image(
        WEAVIATE_LOGO_OLD_ENCODED, distance=distance, certainty=certainty
    )
    assert len(objects) == 2
    assert objects[0].metadata.uuid == uuid1


@pytest.mark.parametrize("which_case", [0, 1, 2, 3])
def test_return_properties_with_typed_dict(collection_basic: Collection, which_case: int):
    name = "TestReturnListWithModel"
    collection_basic.delete(name)
    collection = collection_basic.create(
        name=name,
        vectorizer_config=VectorizerFactory.none(),
        properties=[
            Property(name="int_", data_type=DataType.INT),
            Property(name="ints", data_type=DataType.INT_ARRAY),
        ],
    )
    data = {
        "int_": 1,
        "ints": [1, 2, 3],
    }
    collection.data.insert(properties=data)
    if which_case == 0:

        class DataModel(TypedDict):
            int_: int

        objects = collection.query.get(return_properties=DataModel)
        assert len(objects) == 1
        assert objects[0].properties == {"int_": 1}
    elif which_case == 1:

        class DataModel(TypedDict):
            ints: List[int]

        objects = collection.query.get(return_properties=DataModel)
        assert len(objects) == 1
        assert objects[0].properties == {"ints": [1, 2, 3]}
    elif which_case == 2:

        class DataModel(TypedDict):
            int_: int
            ints: List[int]

        objects = collection.query.get(return_properties=DataModel)
        assert len(objects) == 1
        assert objects[0].properties == data
    elif which_case == 3:

        class DataModel(TypedDict):
            non_existant: str

        with pytest.raises(WeaviateGRPCException):
            collection.query.get(return_properties=DataModel)


@pytest.mark.parametrize(
    "sort,expected",
    [
        (Sort(prop="name", ascending=True), [0, 1, 2]),
        (Sort(prop="name", ascending=False), [2, 1, 0]),
        ([Sort(prop="age", ascending=False), Sort(prop="name", ascending=True)], [1, 2, 0]),
    ],
)
def test_sort(collection_basic: Collection, sort: Union[Sort, List[Sort]], expected: List[int]):
    name = "TestSort"
    collection_basic.delete(name)

    collection = collection_basic.create(
        name="TestSort",
        vectorizer_config=VectorizerFactory.none(),
        properties=[
            Property(name="age", data_type=DataType.INT),
            Property(name="name", data_type=DataType.TEXT),
        ],
    )
    uuids_from = [
        collection.data.insert(properties={"name": "A", "age": 20}),
        collection.data.insert(properties={"name": "B", "age": 22}),
        collection.data.insert(properties={"name": "C", "age": 22}),
    ]

    objects = collection.query.get(sort=sort)
    assert len(objects) == len(expected)

    expected_uuids = [uuids_from[result] for result in expected]
    object_uuids = [obj.metadata.uuid for obj in objects]
    assert object_uuids == expected_uuids


def test_optional_ref_returns(collection_basic: Collection):
    name_target = "TestRefReturnEverything"
    name = "TestInsertManyRefs"
    collection_basic.delete(name_target)
    collection_basic.delete(name)

    ref_collection = collection_basic.create(
        name=name_target,
        vectorizer_config=VectorizerFactory.none(),
        properties=[Property(name="text", data_type=DataType.TEXT)],
    )
    uuid_to1 = ref_collection.data.insert(properties={"text": "ref text"})

    collection = collection_basic.create(
        name=name,
        properties=[
            ReferenceProperty(name="ref", target_collection=name_target),
        ],
        vectorizer_config=VectorizerFactory.none(),
    )
    collection.data.insert(properties={"ref": ReferenceFactory.to(uuid_to1)})

    objects = collection.query.get(return_properties=[LinkTo(link_on="ref")])

    assert objects[0].properties["ref"].objects[0].properties["text"] == "ref text"
    assert objects[0].properties["ref"].objects[0].metadata.uuid is not None
