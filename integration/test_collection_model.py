from typing import List, Optional, Annotated

import pytest as pytest
import uuid

import weaviate
from weaviate.collection.collection_model import (
    CollectionConfigModel,
    BaseProperty,
    PropertyConfig,
    ReferenceTo,
)
from weaviate.weaviate_classes import Vectorizer
from weaviate.weaviate_types import UUIDS

REF_TO_UUID = uuid.uuid4()


class Group(BaseProperty):
    name: str


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    collection = client.collection_model.create(
        CollectionConfigModel(vectorizer=Vectorizer.NONE), Group
    )
    collection.insert(obj=Group(name="Name", uuid=REF_TO_UUID))

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
def test_types(client, member_type, value, optional: bool):
    if optional:
        member_type = Optional[member_type]

    class ModelTypes(BaseProperty):
        name: member_type

    client.collection_model.delete(ModelTypes)
    collection = client.collection_model.create(
        CollectionConfigModel(vectorizer=Vectorizer.NONE), ModelTypes
    )
    uuid_object = collection.insert(ModelTypes(name=value))
    object_get = collection.get_by_id(uuid_object)
    assert object_get.data == ModelTypes(name=value, uuid=uuid_object)

    if optional:
        uuid_object_optional = collection.insert(ModelTypes(name=None))
        object_get_optional = collection.get_by_id(uuid_object_optional)
        assert object_get_optional.data == ModelTypes(name=None, uuid=uuid_object_optional)


@pytest.mark.parametrize(
    "member_type, annotation ,value,expected",
    [
        (str, PropertyConfig(indexFilterable=False), "value", "text"),
        (UUIDS, ReferenceTo(Group), [str(REF_TO_UUID)], "Group"),
        (Optional[UUIDS], ReferenceTo(Group), [str(REF_TO_UUID)], "Group"),
    ],
)
def test_types_annotates(client, member_type, annotation, value, expected: str):
    class ModelTypes(BaseProperty):
        name: Annotated[member_type, annotation]

    client.collection_model.delete(ModelTypes)
    collection = client.collection_model.create(
        CollectionConfigModel(vectorizer=Vectorizer.NONE), ModelTypes
    )
    uuid_object = collection.insert(ModelTypes(name=value))
    object_get = collection.get_by_id(uuid_object)
    assert object_get.data.name == value


@pytest.mark.parametrize("use_name", [True, False])
def test_create_and_delete(client, use_name: bool):
    class DeleteModel(BaseProperty):
        name: int

    client.collection_model.create(CollectionConfigModel(vectorizer=Vectorizer.NONE), DeleteModel)
    model = DeleteModel.__name__ if use_name else DeleteModel

    assert client.collection_model.exists(model)
    client.collection_model.delete(model)
    assert not client.collection_model.exists(model)
