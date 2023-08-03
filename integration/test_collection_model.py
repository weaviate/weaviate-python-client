import sys
from typing import List, Optional

from weaviate import Config

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated
import pytest as pytest
import uuid

import weaviate
from weaviate.weaviate_classes import (
    BaseProperty,
    CollectionModelConfig,
    MultiTenancyConfig,
    PropertyConfig,
    ReferenceTo,
    Tenant,
    Vectorizer,
)
from weaviate.weaviate_types import UUIDS

REF_TO_UUID = uuid.uuid4()


class Group(BaseProperty):
    name: str


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client(
        "http://localhost:8080", additional_config=Config(grpc_port_experimental=50051)
    )
    client.schema.delete_all()
    collection = client.collection_model.create(
        CollectionModelConfig(name="Group", model=Group, vectorizer=Vectorizer.NONE)
    )
    collection.data.insert(obj=Group(name="Name", uuid=REF_TO_UUID))

    yield client
    client.schema.delete_all()


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

    name = "ModelTypes"

    client.collection_model.delete(name)
    collection = client.collection_model.create(
        CollectionModelConfig(name=name, model=ModelTypes, vectorizer=Vectorizer.NONE)
    )
    assert collection._model == ModelTypes

    uuid_object = collection.data.insert(ModelTypes(name=value))
    assert type(uuid_object) is uuid.UUID

    object_get = collection.data.get_by_id(uuid_object)
    assert object_get.data == ModelTypes(name=value, uuid=uuid_object)

    if optional:
        uuid_object_optional = collection.data.insert(ModelTypes(name=None))
        object_get_optional = collection.data.get_by_id(uuid_object_optional)
        assert object_get_optional.data == ModelTypes(name=None, uuid=uuid_object_optional)


@pytest.mark.parametrize(
    "member_type, annotation ,value,expected",
    [
        (str, PropertyConfig(indexFilterable=False), "value", "text"),
        (UUIDS, ReferenceTo(Group), [str(REF_TO_UUID)], "Group"),
        (Optional[UUIDS], ReferenceTo(Group), [str(REF_TO_UUID)], "Group"),
    ],
)
def test_types_annotates(client: weaviate.Client, member_type, annotation, value, expected: str):
    class ModelTypes(BaseProperty):
        name: Annotated[member_type, annotation]

    name = "ModelTypes"
    client.collection_model.delete(name)
    collection = client.collection_model.create(
        CollectionModelConfig(name=name, model=ModelTypes, vectorizer=Vectorizer.NONE)
    )
    assert collection._model == ModelTypes

    uuid_object = collection.data.insert(ModelTypes(name=value))

    object_get = collection.data.get_by_id(uuid_object)
    assert type(object_get.data) is ModelTypes

    assert object_get.data.name == value


def test_create_and_delete(client: weaviate.Client):
    class DeleteModel(BaseProperty):
        name: int

    name = "DeleteModel"
    client.collection_model.create(
        CollectionModelConfig(name=name, model=DeleteModel, vectorizer=Vectorizer.NONE)
    )

    assert client.collection_model.exists(name)
    client.collection_model.delete(name)
    assert not client.collection_model.exists(name)


def test_search(client: weaviate.Client):
    class SearchTest(BaseProperty):
        name: str

    name = "SearchTest"
    client.collection_model.delete(name)
    collection = client.collection_model.create(
        CollectionModelConfig(name=name, model=SearchTest, vectorizer=Vectorizer.NONE)
    )

    collection.data.insert(SearchTest(name="test name"))
    collection.data.insert(SearchTest(name="other words"))

    objects = collection.query.bm25_flat(query="test")
    assert type(objects[0].data) is SearchTest
    assert objects[0].data.name == "test name"


def test_tenants(client: weaviate.Client):
    client.collection.delete("Tenants")
    collection = client.collection.create(
        CollectionModelConfig(
            name="Tenants",
            vectorizer=Vectorizer.NONE,
            multiTenancyConfig=MultiTenancyConfig(
                enabled=True,
            ),
            model=BaseProperty,
        )
    )

    collection.tenants.add([Tenant(name="tenant1")])

    tenants = collection.tenants.get()
    assert len(tenants) == 1
    assert type(tenants[0]) is Tenant
    assert tenants[0].name == "tenant1"

    collection.tenants.remove(["tenant1"])

    tenants = collection.tenants.get()
    assert len(tenants) == 0
