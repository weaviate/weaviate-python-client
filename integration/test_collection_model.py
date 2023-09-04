import sys
from datetime import datetime, timezone
from typing import List, Optional

from pydantic_core._pydantic_core import PydanticUndefined

from weaviate import Config
from weaviate.collection.classes.grpc import MetadataQuery
from weaviate.exceptions import WeaviateAddInvalidPropertyError
from weaviate.weaviate_types import UUIDS

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated
import pytest as pytest
import uuid

import weaviate
from weaviate.collection.classes.config import (
    MultiTenancyConfig,
    PropertyConfig,
    Vectorizer,
)
from weaviate.collection.classes.internal import Reference
from weaviate.collection.classes.orm import BaseProperty, CollectionModelConfig
from weaviate.collection.classes.tenants import Tenant, TenantActivityStatus
from pydantic import Field

REF_TO_UUID = uuid.uuid4()


class Group(BaseProperty):
    name: str


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client(
        "http://localhost:8080", additional_config=Config(grpc_port_experimental=50051)
    )
    client.collection_model.delete(Group)
    collection = client.collection_model.create(
        CollectionModelConfig[Group](model=Group, vectorizer=Vectorizer.NONE)
    )
    collection.data.insert(obj=Group(name="Name", uuid=REF_TO_UUID))

    yield client


def test_with_existing_collection(client: weaviate.Client):
    obj = client.collection_model.get(Group).data.get_by_id(REF_TO_UUID)
    assert obj.properties.name == "Name"


@pytest.mark.parametrize(
    "member_type,value",
    [
        (str, "1"),
        (int, 1),
        (float, 0.5),
        (List[str], ["1", "2"]),
        (List[int], [1, 2]),
        (List[float], [1.0, 2.1]),
    ],
)
@pytest.mark.parametrize("optional", [True, False])
def test_types(client: weaviate.Client, member_type, value, optional: bool):
    if optional:
        member_type = Optional[member_type]

    class ModelTypes(BaseProperty):
        name: member_type

    client.collection_model.delete(ModelTypes)
    collection = client.collection_model.create(
        CollectionModelConfig[ModelTypes](model=ModelTypes, vectorizer=Vectorizer.NONE)
    )
    assert collection.model == ModelTypes

    uuid_object = collection.data.insert(ModelTypes(name=value))
    assert type(uuid_object) is uuid.UUID

    object_get = collection.data.get_by_id(uuid_object)
    assert object_get.properties == ModelTypes(name=value, uuid=uuid_object)

    if optional:
        uuid_object_optional = collection.data.insert(ModelTypes(name=None))
        object_get_optional = collection.data.get_by_id(uuid_object_optional)
        assert object_get_optional.properties == ModelTypes(name=None, uuid=uuid_object_optional)


@pytest.mark.skip(reason="ORM models do not support new references yet")
@pytest.mark.parametrize(
    "member_type, annotation ,value,expected",
    [
        (str, PropertyConfig(index_filterable=False), "value", "text"),
        (UUIDS, Reference[Group], [str(REF_TO_UUID)], "Group"),
        (Optional[UUIDS], Reference[Group], [str(REF_TO_UUID)], "Group"),
    ],
)
def test_types_annotates(client: weaviate.Client, member_type, annotation, value, expected: str):
    class ModelTypes(BaseProperty):
        name: Annotated[member_type, annotation]

    client.collection_model.delete(ModelTypes)
    collection = client.collection_model.create(
        CollectionModelConfig[ModelTypes](model=ModelTypes, vectorizer=Vectorizer.NONE)
    )
    assert collection.model == ModelTypes

    uuid_object = collection.data.insert(ModelTypes(name=value))

    object_get = collection.data.get_by_id(uuid_object)
    assert type(object_get.properties) is ModelTypes

    assert object_get.properties.name == value


def test_create_and_delete(client: weaviate.Client):
    class DeleteModel(BaseProperty):
        name: int

    client.collection_model.delete(DeleteModel)
    client.collection_model.create(
        CollectionModelConfig[DeleteModel](model=DeleteModel, vectorizer=Vectorizer.NONE)
    )

    assert client.collection_model.exists(DeleteModel)
    client.collection_model.delete(DeleteModel)
    assert not client.collection_model.exists(DeleteModel)


def test_search(client: weaviate.Client):
    class SearchTest(BaseProperty):
        name: str

    client.collection_model.delete(SearchTest)
    collection = client.collection_model.create(
        CollectionModelConfig[SearchTest](model=SearchTest, vectorizer=Vectorizer.NONE)
    )

    collection.data.insert(SearchTest(name="test name"))
    collection.data.insert(SearchTest(name="other words"))

    objects = collection.query.bm25_flat(query="test", return_properties=["name"])
    assert type(objects[0].properties) is SearchTest
    assert objects[0].properties.name == "test name"


def test_tenants(client: weaviate.Client):
    class TenantsTest(BaseProperty):
        name: str

    client.collection_model.delete(TenantsTest)
    collection = client.collection_model.create(
        CollectionModelConfig[TenantsTest](
            vectorizer=Vectorizer.NONE,
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
            model=TenantsTest,
        )
    )

    collection.tenants.add([Tenant(name="tenant1")])

    tenants = collection.tenants.get()
    assert len(tenants) == 1
    assert type(tenants["tenant1"]) is Tenant
    assert tenants["tenant1"].name == "tenant1"

    collection.tenants.remove(["tenant1"])

    tenants = collection.tenants.get()
    assert len(tenants) == 0


def test_tenants_activity(client: weaviate.Client):
    class TenantsUpdateTest(BaseProperty):
        name: str

    client.collection_model.delete(TenantsUpdateTest)
    collection = client.collection_model.create(
        CollectionModelConfig[TenantsUpdateTest](
            vectorizer=Vectorizer.NONE,
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
            model=TenantsUpdateTest,
        )
    )
    collection.tenants.add(
        [
            Tenant(name="1", activity_status=TenantActivityStatus.HOT),
            Tenant(name="2", activity_status=TenantActivityStatus.COLD),
            Tenant(name="3"),
        ]
    )
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.HOT
    assert tenants["2"].activity_status == TenantActivityStatus.COLD
    assert tenants["3"].activity_status == TenantActivityStatus.HOT


def test_tenants_update(client: weaviate.Client):
    class TenantsUpdateTest(BaseProperty):
        name: str

    client.collection_model.delete(TenantsUpdateTest)
    collection = client.collection_model.create(
        CollectionModelConfig[TenantsUpdateTest](
            vectorizer=Vectorizer.NONE,
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
            model=TenantsUpdateTest,
        )
    )
    collection.tenants.add([Tenant(name="1", activity_status=TenantActivityStatus.HOT)])
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.HOT

    collection.tenants.update([Tenant(name="1", activity_status=TenantActivityStatus.COLD)])
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.COLD


def test_multi_searches(client: weaviate.Client):
    class TestMultiSearches(BaseProperty):
        name: str

    client.collection_model.delete(TestMultiSearches)
    collection = client.collection_model.create(
        CollectionModelConfig[TestMultiSearches](
            model=TestMultiSearches, vectorizer=Vectorizer.NONE
        )
    )

    collection.data.insert(TestMultiSearches(name="some word"))
    collection.data.insert(TestMultiSearches(name="other"))

    objects = collection.query.bm25_flat(
        query="word",
        return_properties=["name"],
        return_metadata=MetadataQuery(last_update_time_unix=True),
    )
    assert objects[0].properties.name == "some word"
    assert objects[0].metadata.last_update_time_unix is not None

    objects = collection.query.bm25_flat(
        query="other", return_properties=["name"], return_metadata=MetadataQuery(uuid=True)
    )
    assert objects[0].properties.name == "other"
    assert objects[0].metadata.uuid is not None
    assert objects[0].metadata.last_update_time_unix is None


@pytest.mark.skip(reason="ORM models do not support references yet")
def test_multi_searches_with_references(client: weaviate.Client):
    class TestMultiSearchesWithReferences(BaseProperty):
        name: Optional[str] = None
        group: Optional[Reference[Group]] = None

    client.collection_model.delete(TestMultiSearchesWithReferences)
    collection = client.collection_model.create(
        CollectionModelConfig[TestMultiSearchesWithReferences](
            model=TestMultiSearchesWithReferences, vectorizer=Vectorizer.NONE
        )
    )

    collection.data.insert(
        TestMultiSearchesWithReferences(name="some word", group=Reference[Group].to(REF_TO_UUID))
    )
    collection.data.insert(
        TestMultiSearchesWithReferences(name="other", group=Reference[Group].to(REF_TO_UUID))
    )

    objects = collection.query.bm25_flat(
        query="word",
        return_properties=["name", "group"],
        return_metadata=MetadataQuery(last_update_time_unix=True),
    )
    assert objects[0].properties.name == "some word"
    assert objects[0].properties.group.objects == []
    assert objects[0].metadata.last_update_time_unix is not None

    objects = collection.query.bm25_flat(
        query="other",
        return_metadata=MetadataQuery(uuid=True),
    )
    assert objects[0].properties.name is None
    assert objects[0].properties.group is None
    assert objects[0].metadata.uuid is not None
    assert objects[0].metadata.last_update_time_unix is None


def test_search_with_tenant(client: weaviate.Client):
    class TestTenantSearch(BaseProperty):
        name: str

    client.collection_model.delete(TestTenantSearch)
    collection = client.collection_model.create(
        CollectionModelConfig[TestTenantSearch](
            model=TestTenantSearch,
            vectorizer=Vectorizer.NONE,
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
        )
    )

    collection.tenants.add([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")
    uuid1 = tenant1.data.insert(TestTenantSearch(name="some"))
    objects1 = tenant1.query.bm25_flat(
        query="some", return_properties=["name"], return_metadata=MetadataQuery(uuid=True)
    )
    assert len(objects1) == 1
    assert objects1[0].metadata.uuid == uuid1

    objects2 = tenant2.query.bm25_flat(query="some", return_metadata=MetadataQuery(uuid=True))
    assert len(objects2) == 0


def make_list() -> List[int]:
    return []


@pytest.mark.parametrize(
    "member_type, value_to_add,default,default_factory, exception",
    [
        (int, 10, 5, None, True),
        (int, 10, PydanticUndefined, None, True),
        (Optional[int], 10, PydanticUndefined, None, False),
        (Optional[int], 10, None, None, False),
        (Optional[int], 10, 10, None, False),
        (List[int], [10], None, None, True),
        (Optional[List[int]], [10], None, None, False),
        (List[int], [10], None, make_list, True),
    ],
)
def test_update_properties(
    client: weaviate.Client,
    member_type: type,
    value_to_add,
    default,
    default_factory,
    exception: bool,
):
    uuid_first: Optional[uuid.UUID] = None

    def create_original_collection():
        nonlocal uuid_first
        # class definition will be gone when this is out of scope

        class TestPropUpdate(BaseProperty):
            name: str

        client.collection_model.delete(TestPropUpdate)
        collection_first = client.collection_model.create(
            CollectionModelConfig[TestPropUpdate](model=TestPropUpdate, vectorizer=Vectorizer.NONE)
        )
        uuid_first = collection_first.data.insert(TestPropUpdate(name="first"))

    create_original_collection()

    field = Field()
    if default_factory is not None:
        field = Field(default_factory=default_factory)
    elif default is not None:
        field = Field(default=default)

    class TestPropUpdate(BaseProperty):
        name: str
        number: member_type = field

    if exception:
        with pytest.raises(WeaviateAddInvalidPropertyError):
            client.collection_model.update(TestPropUpdate)
    else:
        collection = client.collection_model.update(TestPropUpdate)
        uuid_second = collection.data.insert(TestPropUpdate(name="second", number=value_to_add))
        objects = collection.data.get()
        assert len(objects) == 2
        assert uuid_first is not None
        first = collection.data.get_by_id(uuid_first)

        assert first.properties.name == "first"
        assert (
            first.properties.number == default
            if default is not None and default != PydanticUndefined
            else default_factory()
            if default_factory is not None
            else first.properties.number is None
        )

        second = collection.data.get_by_id(uuid_second)
        assert second.properties.name == "second"
        assert second.properties.number == value_to_add


def test_empty_search_returns_everything(client: weaviate.Client):
    class TestReturnEverythingORM(BaseProperty):
        name: Optional[str] = None

    client.collection_model.delete(TestReturnEverythingORM)
    collection = client.collection_model.create(
        CollectionModelConfig[TestReturnEverythingORM](
            model=TestReturnEverythingORM,
            vectorizer=Vectorizer.NONE,
        )
    )
    collection.data.insert(TestReturnEverythingORM(name="word"))

    objects = collection.query.bm25_flat(query="word")
    assert objects[0].properties.name is not None
    assert objects[0].properties.name == "word"
    assert objects[0].metadata.uuid is not None
    assert objects[0].metadata.score is not None
    assert objects[0].metadata.last_update_time_unix is not None
    assert objects[0].metadata.creation_time_unix is not None


@pytest.mark.skip(reason="ORM models do not support empty properties in search yet")
def test_empty_return_properties(client: weaviate.Client):
    class TestEmptyProperties(BaseProperty):
        name: str

    client.collection_model.delete(TestEmptyProperties)
    collection = client.collection_model.create(
        CollectionModelConfig[TestEmptyProperties](
            model=TestEmptyProperties,
            vectorizer=Vectorizer.NONE,
        )
    )
    collection.data.insert(TestEmptyProperties(name="word"))

    objects = collection.query.bm25_flat(query="word", return_metadata=MetadataQuery(uuid=True))
    assert objects[0].properties.name is None


@pytest.mark.skip(reason="ORM models do not support updating reference properties yet")
def test_update_reference_property(client: weaviate.Client):
    uuid_first: Optional[uuid.UUID] = None

    def create_original_collection():
        nonlocal uuid_first
        # class definition will be gone when this is out of scope

        class TestRefPropUpdate(BaseProperty):
            name: str

        client.collection_model.delete(TestRefPropUpdate)
        collection_first = client.collection_model.create(
            CollectionModelConfig[TestRefPropUpdate](
                model=TestRefPropUpdate, vectorizer=Vectorizer.NONE
            )
        )
        uuid_first = collection_first.data.insert(TestRefPropUpdate(name="first"))

    class TestRefPropUpdate(BaseProperty):
        name: str
        group: Reference[Group]

    create_original_collection()
    client.collection_model.update(TestRefPropUpdate)


def test_model_with_datetime_property(client: weaviate.Client):
    class TestDatetime(BaseProperty):
        name: str
        date: datetime

    client.collection_model.delete(TestDatetime)
    collection = client.collection_model.create(
        CollectionModelConfig[TestDatetime](model=TestDatetime, vectorizer=Vectorizer.NONE)
    )
    now = datetime.now(timezone.utc)
    collection.data.insert(TestDatetime(name="test", date=now))
    objects = collection.data.get()
    assert len(objects) == 1
    assert objects[0].properties.name == "test"
    assert type(objects[0].properties.date) is datetime

    # assert objects[0].properties.date == now
    # The same issue as in test_collection.py@introduce_date_parsing_to_collections occurs here
    # Weaviate parsing of dates is not perfectly compatible with the python datetime library
