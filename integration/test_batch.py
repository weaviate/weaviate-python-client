import uuid
from dataclasses import dataclass
from typing import List, Union, Sequence, Optional

import pytest

import weaviate
from weaviate import Tenant
from weaviate.gql.filter import VALUE_ARRAY_TYPES, WHERE_OPERATORS

UUID = Union[str, uuid.UUID]


def has_batch_errors(results: dict) -> bool:
    """
    Check batch results for errors.

    Parameters
    ----------
    results : dict
        The Weaviate batch creation return value.
    """

    if results is not None:
        for result in results:
            if "result" in result and "errors" in result["result"]:
                if "error" in result["result"]["errors"]:
                    return True
    return False


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
def client():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create_class(
        {
            "class": "Test",
            "properties": [
                {"name": "test", "dataType": ["Test"]},
                {"name": "name", "dataType": ["string"]},
                {"name": "names", "dataType": ["string[]"]},
            ],
            "vectorizer": "none",
        }
    )
    yield client
    client.schema.delete_all()


@pytest.mark.parametrize(
    "vector",
    [None, [1, 2, 3], MockNumpyTorch([1, 2, 3]), MockTensorFlow([1, 2, 3])],
)
@pytest.mark.parametrize("uuid", [None, uuid.uuid4(), str(uuid.uuid4()), uuid.uuid4().hex])
def test_add_data_object(client: weaviate.Client, uuid: Optional[UUID], vector: Optional[Sequence]):
    """Test the `add_data_object` method"""
    client.batch.add_data_object(
        data_object={},
        class_name="Test",
        uuid=uuid,
        vector=vector,
    )
    response = client.batch.create_objects()
    assert has_batch_errors(response) is False, str(response)


@pytest.mark.parametrize(
    "objs,where",
    [
        (
            [
                {"name": "zero"},
            ],
            {
                "path": ["name"],
                "operator": "NotEqual",
                "valueText": "one",
            },
        ),
        (
            [
                {"name": "one"},
            ],
            {
                "path": ["name"],
                "operator": "Equal",
                "valueText": "one",
            },
        ),
        (
            [{"name": "two"}, {"name": "three"}],
            {
                "path": ["name"],
                "operator": "ContainsAny",
                "valueTextArray": ["two", "three"],
            },
        ),
        (
            [
                {"names": ["Tim", "Tom"], "name": "four"},
            ],
            {
                "path": ["names"],
                "operator": "ContainsAll",
                "valueTextArray": ["Tim", "Tom"],
            },
        ),
        (
            [
                {"names": ["Tim", "Tom"], "name": "five"},
            ],
            {
                "operator": "And",
                "operands": [
                    {
                        "path": ["names"],
                        "operator": "ContainsAll",
                        "valueTextArray": ["Tim", "Tom"],
                    },
                    {
                        "path": ["name"],
                        "operator": "Equal",
                        "valueText": "five",
                    },
                ],
            },
        ),
        (
            [{"name": "six"}, {"name": "seven"}],
            {
                "operator": "Or",
                "operands": [
                    {
                        "path": ["name"],
                        "operator": "Equal",
                        "valueText": "six",
                    },
                    {
                        "path": ["name"],
                        "operator": "Equal",
                        "valueText": "seven",
                    },
                ],
            },
        ),
        (
            [
                {"name": "eight"},
            ],
            {
                "path": ["name"],
                "operator": "Like",
                "valueText": "eig*",
            },
        ),
    ],
)
def test_delete_objects_successes(client: weaviate.Client, objs: List[dict], where: dict):
    with client.batch as batch:
        for obj in objs:
            batch.add_data_object(data_object=obj, class_name="Test")

    with client.batch as batch:
        batch.delete_objects(
            "Test",
            where=where,
        )
    res = client.data_object.get()
    names = [obj["properties"]["name"] for obj in res["objects"]]
    for obj in objs:
        assert obj.get("name") not in names


def test_delete_objects_errors(client: weaviate.Client):
    with pytest.raises(ValueError) as error:
        with client.batch as batch:
            batch.delete_objects(
                "test",
                where={
                    "path": ["name"],
                    "operator": "ContainsAny",
                    "valueText": ["four"],
                },
            )
    assert (
        error.value.args[0]
        == f"Operator 'ContainsAny' is not supported for value type 'valueText'. Supported value types are: {VALUE_ARRAY_TYPES}"
    )

    where = {
        "path": ["name"],
        "valueTextArray": ["four"],
    }
    with pytest.raises(ValueError) as error:
        with client.batch as batch:
            batch.delete_objects(
                "Test",
                where=where,
            )
    assert (
        error.value.args[0] == f"Where filter is missing required field `operator`. Given: {where}"
    )

    with pytest.raises(ValueError) as error:
        with client.batch as batch:
            batch.delete_objects(
                "Test",
                where={
                    "path": ["name"],
                    "operator": "Wrong",
                    "valueText": ["four"],
                },
            )
    assert (
        error.value.args[0]
        == f"Operator Wrong is not allowed. Allowed operators are: {WHERE_OPERATORS}"
    )


@pytest.mark.parametrize("from_object_uuid", [uuid.uuid4(), str(uuid.uuid4()), uuid.uuid4().hex])
@pytest.mark.parametrize("to_object_uuid", [uuid.uuid4().hex, uuid.uuid4(), str(uuid.uuid4())])
@pytest.mark.parametrize("to_object_class_name", [None, "Test"])
def test_add_reference(
    client: weaviate.Client,
    from_object_uuid: UUID,
    to_object_uuid: UUID,
    to_object_class_name: Optional[str],
):
    """Test the `add_reference` method"""

    # create the 2 objects first
    client.data_object.create(
        data_object={},
        class_name="Test",
        uuid=from_object_uuid,
    )
    client.data_object.create(
        data_object={},
        class_name="Test",
        uuid=to_object_uuid,
    )

    client.batch.add_reference(
        from_object_uuid=from_object_uuid,
        from_object_class_name="Test",
        from_property_name="test",
        to_object_uuid=to_object_uuid,
        to_object_class_name=to_object_class_name,
    )

    response = client.batch.create_references()
    assert has_batch_errors(response) is False, str(response)


def test_add_object_batch_with_tenant():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()

    # create two classes and add 5 tenants each
    class_names = ["BatchTestMultiTenant1", "BatchTestMultiTenant2"]
    for name in class_names:
        client.schema.create_class(
            {
                "class": name,
                "vectorizer": "none",
                "properties": [
                    {"name": "tenantAsProp", "dataType": ["text"]},
                ],
                "multiTenancyConfig": {"enabled": True},
            },
        )
        client.schema.add_class_tenants(name, [Tenant("tenant" + str(i)) for i in range(5)])

    nr_objects = 100
    objects = []
    with client.batch() as batch:
        for i in range(nr_objects):
            obj_uuid = uuid.uuid4()
            objects.append((obj_uuid, class_names[i % 2], "tenant" + str(i % 5)))
            batch.add_data_object(
                class_name=class_names[i % 2],
                tenant="tenant" + str(i % 5),
                data_object={"tenantAsProp": "tenant" + str(i % 5)},
                uuid=obj_uuid,
            )

    for obj in objects:
        retObj = client.data_object.get_by_id(obj[0], class_name=obj[1], tenant=obj[2])
        assert retObj["properties"]["tenantAsProp"] == obj[2]

    # test batch delete with wrong tenant id
    with client.batch() as batch:
        batch.delete_objects(
            class_name=objects[0][1],
            where={
                "path": ["tenantAsProp"],
                "operator": "Equal",
                "valueString": objects[0][2],
            },
            tenant=objects[1][2],
        )

        retObj = client.data_object.get_by_id(
            objects[0][0], class_name=objects[0][1], tenant=objects[0][2]
        )
        assert retObj["properties"]["tenantAsProp"] == objects[0][2]

    # test batch delete with correct tenant id
    with client.batch() as batch:
        batch.delete_objects(
            class_name=objects[0][1],
            where={
                "path": ["tenantAsProp"],
                "operator": "Equal",
                "valueString": objects[0][2],
            },
            tenant=objects[0][2],
        )

        retObj = client.data_object.get_by_id(
            objects[0][0], class_name=objects[0][1], tenant=objects[0][2]
        )
        assert retObj is None

    for name in class_names:
        client.schema.delete_class(name)


def test_add_ref_batch_with_tenant():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()

    # create two classes and add 5 tenants each
    class_names = ["BatchRefTestMultiTenant0", "BatchRefTestMultiTenant1"]
    client.schema.create_class(
        {
            "class": class_names[0],
            "vectorizer": "none",
            "multiTenancyConfig": {"enabled": True},
        },
    )

    client.schema.create_class(
        {
            "class": class_names[1],
            "vectorizer": "none",
            "properties": [
                {"name": "tenantAsProp", "dataType": ["text"]},
                {"name": "ref", "dataType": [class_names[0]]},
            ],
            "multiTenancyConfig": {"enabled": True},
        },
    )

    for name in class_names:
        client.schema.add_class_tenants(name, [Tenant("tenant" + str(i)) for i in range(5)])

    nr_objects = 100
    objects_class0 = []
    objects_class1 = []
    with client.batch() as batch:
        for i in range(nr_objects):
            tenant = "tenant" + str(i % 5)
            obj_uuid0 = uuid.uuid4()
            objects_class0.append(obj_uuid0)
            batch.add_data_object(
                class_name=class_names[0], tenant=tenant, data_object={}, uuid=obj_uuid0
            )

            obj_uuid1 = uuid.uuid4()
            objects_class1.append((obj_uuid1, "tenant" + str(i % 5)))
            batch.add_data_object(
                class_name=class_names[1],
                tenant=tenant,
                data_object={"tenantAsProp": tenant},
                uuid=obj_uuid1,
            )

            # add refs between classes for all tenants
            batch.add_reference(
                from_property_name="ref",
                from_object_class_name=class_names[1],
                from_object_uuid=obj_uuid1,
                to_object_class_name=class_names[0],
                to_object_uuid=obj_uuid0,
                tenant=tenant,
            )

    for i, obj in enumerate(objects_class1):
        ret_obj = client.data_object.get_by_id(obj[0], class_name=class_names[1], tenant=obj[1])
        assert ret_obj["properties"]["tenantAsProp"] == obj[1]
        assert (
            ret_obj["properties"]["ref"][0]["beacon"]
            == f"weaviate://localhost/{class_names[0]}/{objects_class0[i]}"
        )

    for name in reversed(class_names):
        client.schema.delete_class(name)


def test_add_nested_object_with_batch():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()

    client.schema.create_class(
        {
            "class": "BatchTestNested",
            "vectorizer": "none",
            "properties": [
                {
                    "name": "nested",
                    "dataType": ["object"],
                    "nestedProperties": [
                        {"name": "name", "dataType": ["text"]},
                        {"name": "names", "dataType": ["text[]"]},
                    ],
                }
            ],
        },
    )

    uuid_ = uuid.uuid4()
    with client.batch as batch:
        batch.add_data_object(
            class_name="BatchTestNested",
            data_object={"nested": {"name": "nested", "names": ["nested1", "nested2"]}},
            uuid=uuid_,
        )

    obj = client.data_object.get_by_id(uuid_, class_name="BatchTestNested")
    assert obj["properties"]["nested"] == {"name": "nested", "names": ["nested1", "nested2"]}
