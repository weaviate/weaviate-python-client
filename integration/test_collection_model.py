import pytest as pytest

pytest.skip(allow_module_level=True)

# import sys
# from datetime import datetime, timezone
# from typing import List, Optional

# from pydantic_core._pydantic_core import PydanticUndefined

# from weaviate.collections.classes.grpc import MetadataQuery
# from weaviate.exceptions import WeaviateAddInvalidPropertyError
# from weaviate.types import UUIDS

# if sys.version_info < (3, 9):
#     from typing_extensions import Annotated
# else:
#     from typing import Annotated
# import uuid

# import weaviate
# from weaviate.collections.classes.config import (
#     Configure,
#     _PropertyConfig,
# )
# from weaviate.collections.classes.internal import CrossReference
# from weaviate.collections.classes.orm import BaseProperty, CollectionModelConfig
# from weaviate.collections.classes.tenants import Tenant, TenantActivityStatus
# from pydantic import Field

# REF_TO_UUID = uuid.uuid4()


# class Group(BaseProperty):
#     name: str


# @pytest.fixture(scope="module")
# def client():
#     connection_params = weaviate.connect.ConnectionParams.from_url("http://localhost:8080", 50051)
#     client = weaviate.WeaviateClient(connection_params)
#     client._collection_model.delete(Group)
#     collection = client._collection_model.create(
#         CollectionModelConfig[Group](model=Group, vectorizer_config=Configure.Vectorizer.none())
#     )
#     collection.data.insert(obj=Group(name="Name", uuid=REF_TO_UUID))

#     yield client


# def test_with_existing_collection(client: weaviate.WeaviateClient):
#     obj = client._collection_model.get(Group).data.get_by_id(REF_TO_UUID)
#     assert obj.properties.name == "Name"


# @pytest.mark.parametrize(
#     "member_type,value",
#     [
#         (str, "1"),
#         (int, 1),
#         (float, 0.5),
#         (List[str], ["1", "2"]),
#         (List[int], [1, 2]),
#         (List[float], [1.0, 2.1]),
#     ],
# )
# @pytest.mark.parametrize("optional", [True, False])
# def test_types(client: weaviate.WeaviateClient, member_type, value, optional: bool):
#     if optional:
#         member_type = Optional[member_type]

#     class ModelTypes(BaseProperty):
#         name: member_type

#     client._collection_model.delete(ModelTypes)
#     collection = client._collection_model.create(
#         CollectionModelConfig[ModelTypes](
#             model=ModelTypes, vectorizer_config=Configure.Vectorizer.none()
#         )
#     )
#     assert collection.model == ModelTypes

#     uuid_object = collection.data.insert(ModelTypes(name=value))
#     assert type(uuid_object) is uuid.UUID

#     object_get = collection.data.get_by_id(uuid_object)
#     assert object_get.properties == ModelTypes(name=value, uuid=uuid_object)

#     if optional:
#         uuid_object_optional = collection.data.insert(ModelTypes(name=None))
#         object_get_optional = collection.data.get_by_id(uuid_object_optional)
#         assert object_get_optional.properties == ModelTypes(name=None, uuid=uuid_object_optional)


# @pytest.mark.skip(reason="ORM models do not support new references yet")
# @pytest.mark.parametrize(
#     "member_type, annotation ,value,expected",
#     [
#         (str, _PropertyConfig(index_filterable=False), "value", "text"),
#         (UUIDS, CrossReference[Group], [str(REF_TO_UUID)], "Group"),
#         (Optional[UUIDS], CrossReference[Group], [str(REF_TO_UUID)], "Group"),
#     ],
# )
# def test_types_annotates(
#     client: weaviate.WeaviateClient, member_type, annotation, value, expected: str
# ):
#     class ModelTypes(BaseProperty):
#         name: Annotated[member_type, annotation]

#     client._collection_model.delete(ModelTypes)
#     collection = client._collection_model.create(
#         CollectionModelConfig[ModelTypes](
#             model=ModelTypes, vectorizer_config=Configure.Vectorizer.none()
#         )
#     )
#     assert collection.model == ModelTypes

#     uuid_object = collection.data.insert(ModelTypes(name=value))

#     object_get = collection.data.get_by_id(uuid_object)
#     assert type(object_get.properties) is ModelTypes

#     assert object_get.properties.name == value


# def test_create_and_delete(client: weaviate.WeaviateClient):
#     class DeleteModel(BaseProperty):
#         name: int

#     client._collection_model.delete(DeleteModel)
#     client._collection_model.create(
#         CollectionModelConfig[DeleteModel](
#             model=DeleteModel, vectorizer_config=Configure.Vectorizer.none()
#         )
#     )

#     assert client._collection_model.exists(DeleteModel)
#     client._collection_model.delete(DeleteModel)
#     assert not client._collection_model.exists(DeleteModel)


# def test_search(client: weaviate.WeaviateClient):
#     class SearchTest(BaseProperty):
#         name: str

#     client._collection_model.delete(SearchTest)
#     collection = client._collection_model.create(
#         CollectionModelConfig[SearchTest](
#             model=SearchTest, vectorizer_config=Configure.Vectorizer.none()
#         )
#     )

#     collection.data.insert(SearchTest(name="test name"))
#     collection.data.insert(SearchTest(name="other words"))

#     objects = collection.query.bm25(query="test", return_properties=["name"])
#     assert type(objects[0].properties) is SearchTest
#     assert objects[0].properties.name == "test name"


# def test_tenants(client: weaviate.WeaviateClient):
#     class TenantsTest(BaseProperty):
#         name: str

#     client._collection_model.delete(TenantsTest)
#     collection = client._collection_model.create(
#         CollectionModelConfig[TenantsTest](
#             vectorizer_config=Configure.Vectorizer.none(),
#             multi_tenancy_config=Configure.multi_tenancy(enabled=True),
#             model=TenantsTest,
#         )
#     )

#     collection.tenants.create([Tenant(name="tenant1")])

#     tenants = collection.tenants.get()
#     assert len(tenants) == 1
#     assert type(tenants["tenant1"]) is Tenant
#     assert tenants["tenant1"].name == "tenant1"

#     collection.tenants.remove(["tenant1"])

#     tenants = collection.tenants.get()
#     assert len(tenants) == 0


# def test_tenants_activity(client: weaviate.WeaviateClient):
#     class TenantsUpdateTest(BaseProperty):
#         name: str

#     client._collection_model.delete(TenantsUpdateTest)
#     collection = client._collection_model.create(
#         CollectionModelConfig[TenantsUpdateTest](
#             vectorizer_config=Configure.Vectorizer.none(),
#             multi_tenancy_config=Configure.multi_tenancy(enabled=True),
#             model=TenantsUpdateTest,
#         )
#     )
#     collection.tenants.create(
#         [
#             Tenant(name="1", activity_status=TenantActivityStatus.HOT),
#             Tenant(name="2", activity_status=TenantActivityStatus.COLD),
#             Tenant(name="3"),
#         ]
#     )
#     tenants = collection.tenants.get()
#     assert tenants["1"].activity_status == TenantActivityStatus.HOT
#     assert tenants["2"].activity_status == TenantActivityStatus.COLD
#     assert tenants["3"].activity_status == TenantActivityStatus.HOT


# def test_tenants_update(client: weaviate.WeaviateClient):
#     class TenantsUpdateTest(BaseProperty):
#         name: str

#     client._collection_model.delete(TenantsUpdateTest)
#     collection = client._collection_model.create(
#         CollectionModelConfig[TenantsUpdateTest](
#             vectorizer_config=Configure.Vectorizer.none(),
#             multi_tenancy_config=Configure.multi_tenancy(enabled=True),
#             model=TenantsUpdateTest,
#         )
#     )
#     collection.tenants.create([Tenant(name="1", activity_status=TenantActivityStatus.HOT)])
#     tenants = collection.tenants.get()
#     assert tenants["1"].activity_status == TenantActivityStatus.HOT

#     collection.tenants.update([Tenant(name="1", activity_status=TenantActivityStatus.COLD)])
#     tenants = collection.tenants.get()
#     assert tenants["1"].activity_status == TenantActivityStatus.COLD


# def test_multi_searches(client: weaviate.WeaviateClient):
#     class TestMultiSearches(BaseProperty):
#         name: str

#     client._collection_model.delete(TestMultiSearches)
#     collection = client._collection_model.create(
#         CollectionModelConfig[TestMultiSearches](
#             model=TestMultiSearches, vectorizer_config=Configure.Vectorizer.none()
#         )
#     )

#     collection.data.insert(TestMultiSearches(name="some word"))
#     collection.data.insert(TestMultiSearches(name="other"))

#     objects = collection.query.bm25(
#         query="word",
#         return_properties=["name"],
#         return_metadata=MetadataQuery(last_update_time=True),
#     )
#     assert objects[0].properties.name == "some word"
#     assert objects[0].metadata.last_update_time_unix is not None

#     objects = collection.query.bm25(
#         query="other", return_properties=["name"], return_metadata=MetadataQuery(uuid=True)
#     )
#     assert objects[0].properties.name == "other"
#     assert objects[0].metadata.uuid is not None
#     assert objects[0].metadata.last_update_time_unix is None


# # @pytest.mark.skip(reason="ORM models do not support references yet")
# # def test_multi_searches_with_references(client: weaviate.WeaviateClient):
# #     class TestMultiSearchesWithReferences(BaseProperty):
# #         name: Optional[str] = None
# #         group: Optional[CrossReference[Group]] = None  # type: ignore

# #     client._collection_model.delete(TestMultiSearchesWithReferences)
# #     collection = client._collection_model.create(
# #         CollectionModelConfig[TestMultiSearchesWithReferences](
# #             model=TestMultiSearchesWithReferences, vectorizer_config=Configure.Vectorizer.none()
# #         )
# #     )

# #     collection.data.insert(
# #         TestMultiSearchesWithReferences(name="some word", group=Reference.to(REF_TO_UUID, Group))
# #     )
# #     collection.data.insert(
# #         TestMultiSearchesWithReferences(name="other", group=Reference.to(REF_TO_UUID, Group))
# #     )

# #     objects = collection.query.bm25(
# #         query="word",
# #         return_properties=["name", "group"],
# #         return_metadata=MetadataQuery(last_update_time=True),
# #     )
# #     assert objects[0].properties.name == "some word"
# #     assert objects[0].properties.group.objects == []
# #     assert objects[0].metadata.last_update_time_unix is not None

# #     objects = collection.query.bm25(
# #         query="other",
# #         return_metadata=MetadataQuery(uuid=True),
# #     )
# #     assert objects[0].properties.name is None
# #     assert objects[0].properties.group is None
# #     assert objects[0].metadata.uuid is not None
# #     assert objects[0].metadata.last_update_time_unix is None


# def test_search_with_tenant(client: weaviate.WeaviateClient):
#     class TestTenantSearch(BaseProperty):
#         name: str

#     client._collection_model.delete(TestTenantSearch)
#     collection = client._collection_model.create(
#         CollectionModelConfig[TestTenantSearch](
#             model=TestTenantSearch,
#             vectorizer_config=Configure.Vectorizer.none(),
#             multi_tenancy_config=Configure.multi_tenancy(enabled=True),
#         )
#     )

#     collection.tenants.create([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
#     tenant1 = collection.with_tenant("Tenant1")
#     tenant2 = collection.with_tenant("Tenant2")
#     uuid1 = tenant1.data.insert(TestTenantSearch(name="some"))
#     objects1 = tenant1.query.bm25(
#         query="some", return_properties=["name"], return_metadata=MetadataQuery(uuid=True)
#     )
#     assert len(objects1) == 1
#     assert objects1[0].metadata.uuid == uuid1

#     objects2 = tenant2.query.bm25(query="some", return_metadata=MetadataQuery(uuid=True))
#     assert len(objects2) == 0


# def make_list() -> List[int]:
#     return []


# @pytest.mark.parametrize(
#     "member_type, value_to_add,default,default_factory, exception",
#     [
#         (int, 10, 5, None, True),
#         (int, 10, PydanticUndefined, None, True),
#         (Optional[int], 10, PydanticUndefined, None, False),
#         (Optional[int], 10, None, None, False),
#         (Optional[int], 10, 10, None, False),
#         (List[int], [10], None, None, True),
#         (Optional[List[int]], [10], None, None, False),
#         (List[int], [10], None, make_list, True),
#     ],
# )
# def test_update_properties(
#     client: weaviate.WeaviateClient,
#     member_type: type,
#     value_to_add,
#     default,
#     default_factory,
#     exception: bool,
# ):
#     uuid_first: Optional[uuid.UUID] = None

#     def create_original_collection():
#         nonlocal uuid_first
#         # class definition will be gone when this is out of scope

#         class TestPropUpdate(BaseProperty):
#             name: str

#         client._collection_model.delete(TestPropUpdate)
#         collection_first = client._collection_model.create(
#             CollectionModelConfig[TestPropUpdate](
#                 model=TestPropUpdate, vectorizer_config=Configure.Vectorizer.none()
#             )
#         )
#         uuid_first = collection_first.data.insert(TestPropUpdate(name="first"))

#     create_original_collection()

#     field = Field()
#     if default_factory is not None:
#         field = Field(default_factory=default_factory)
#     elif default is not None:
#         field = Field(default=default)

#     class TestPropUpdate(BaseProperty):
#         name: str
#         number: member_type = field  # type: ignore

#     if exception:
#         with pytest.raises(WeaviateAddInvalidPropertyError):
#             client._collection_model.update(TestPropUpdate)
#     else:
#         collection = client._collection_model.update(TestPropUpdate)
#         uuid_second = collection.data.insert(TestPropUpdate(name="second", number=value_to_add))
#         objects = collection.data.get()
#         assert len(objects) == 2
#         assert uuid_first is not None
#         first = collection.data.get_by_id(uuid_first)

#         assert first.properties.name == "first"
#         assert (
#             first.properties.number == default
#             if default is not None and default != PydanticUndefined
#             else default_factory()
#             if default_factory is not None
#             else first.properties.number is None
#         )

#         second = collection.data.get_by_id(uuid_second)
#         assert second.properties.name == "second"
#         assert second.properties.number == value_to_add


# def test_empty_search_returns_everything(client: weaviate.WeaviateClient):
#     class TestReturnEverythingORM(BaseProperty):
#         name: Optional[str] = None

#     client._collection_model.delete(TestReturnEverythingORM)
#     collection = client._collection_model.create(
#         CollectionModelConfig[TestReturnEverythingORM](
#             model=TestReturnEverythingORM,
#             vectorizer_config=Configure.Vectorizer.none(),
#         )
#     )
#     collection.data.insert(TestReturnEverythingORM(name="word"))

#     objects = collection.query.bm25(query="word")
#     assert objects[0].properties.name is not None
#     assert objects[0].properties.name == "word"
#     assert objects[0].metadata.uuid is not None
#     assert objects[0].metadata.score is not None
#     assert objects[0].metadata.last_update_time_unix is not None
#     assert objects[0].metadata.creation_time_unix is not None


# @pytest.mark.skip(reason="ORM models do not support empty properties in search yet")
# def test_empty_return_properties(client: weaviate.WeaviateClient):
#     class TestEmptyProperties(BaseProperty):
#         name: str

#     client._collection_model.delete(TestEmptyProperties)
#     collection = client._collection_model.create(
#         CollectionModelConfig[TestEmptyProperties](
#             model=TestEmptyProperties,
#             vectorizer_config=Configure.Vectorizer.none(),
#         )
#     )
#     collection.data.insert(TestEmptyProperties(name="word"))

#     objects = collection.query.bm25(query="word", return_metadata=MetadataQuery(uuid=True))
#     assert objects[0].properties.name is None


# @pytest.mark.skip(reason="ORM models do not support updating reference properties yet")
# def test_update_reference_property(client: weaviate.WeaviateClient):
#     uuid_first: Optional[uuid.UUID] = None

#     def create_original_collection():
#         nonlocal uuid_first
#         # class definition will be gone when this is out of scope

#         class TestRefPropUpdate(BaseProperty):
#             name: str

#         client._collection_model.delete(TestRefPropUpdate)
#         collection_first = client._collection_model.create(
#             CollectionModelConfig[TestRefPropUpdate](
#                 model=TestRefPropUpdate, vectorizer_config=Configure.Vectorizer.none()
#             )
#         )
#         uuid_first = collection_first.data.insert(TestRefPropUpdate(name="first"))

#     class TestRefPropUpdate(BaseProperty):
#         name: str
#         group: CrossReference[Group]  # type: ignore

#     create_original_collection()
#     client._collection_model.update(TestRefPropUpdate)


# def test_model_with_datetime_property(client: weaviate.WeaviateClient):
#     class TestDatetime(BaseProperty):
#         name: str
#         date: datetime

#     client._collection_model.delete(TestDatetime)
#     collection = client._collection_model.create(
#         CollectionModelConfig[TestDatetime](
#             model=TestDatetime, vectorizer_config=Configure.Vectorizer.none()
#         )
#     )
#     now = datetime.now(timezone.utc)
#     collection.data.insert(TestDatetime(name="test", date=now))
#     objects = collection.data.get()
#     assert len(objects) == 1
#     assert objects[0].properties.name == "test"
#     assert type(objects[0].properties.date) is datetime

#     # assert objects[0].properties.date == now
#     # The same issue as in test_collection.py@introduce_date_parsing_to_collections occurs here
#     # Weaviate parsing of dates is not perfectly compatible with the python datetime library
