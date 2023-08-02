import sys
from typing import List, Optional

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
    PropertyConfig,
    ReferenceTo,
    Vectorizer,
)
from weaviate.weaviate_types import UUIDS

REF_TO_UUID = uuid.uuid4()


class Group(BaseProperty):
    name: str


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
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
    uuid_object = collection.data.insert(ModelTypes(name=value))
    object_get = collection.get_by_id(uuid_object)
    assert object_get.data == ModelTypes(name=value, uuid=uuid_object)

    if optional:
        uuid_object_optional = collection.data.insert(ModelTypes(name=None))
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
def test_types_annotates(client: weaviate.Client, member_type, annotation, value, expected: str):
    class ModelTypes(BaseProperty):
        name: Annotated[member_type, annotation]

    name = "ModelTypes"
    client.collection_model.delete(name)
    collection = client.collection_model.create(
        CollectionModelConfig(name=name, model=ModelTypes, vectorizer=Vectorizer.NONE)
    )
    uuid_object = collection.data.insert(ModelTypes(name=value))
    object_get = collection.get_by_id(uuid_object)
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
