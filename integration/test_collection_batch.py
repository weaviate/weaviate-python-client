import uuid
from dataclasses import dataclass
from typing import List, Union, Sequence, Optional

import pytest

import weaviate
from weaviate import Config
from weaviate.collection.batch import (
    ObjectsBatchRequest,
)
from weaviate.collection.classes.batch import _BatchObjectReturn
from weaviate.collection.classes.config import (
    CollectionConfig,
    DataType,
    MultiTenancyConfig,
    Property,
    ReferenceProperty,
)
from weaviate.collection.classes.tenants import Tenant
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
    client = weaviate.Client(
        "http://localhost:8080", additional_config=Config(grpc_port_experimental=50051)
    )
    client.schema.delete_all()
    client.collection.create(
        CollectionConfig(
            name="Test",
            properties=[
                ReferenceProperty(name="test", target_collection="Test"),
                Property(name="name", data_type=DataType.TEXT),
                Property(name="age", data_type=DataType.INT),
            ],
        )
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
    with client.collection.batch as batch:
        batch.add_object(
            class_name="Test",
            properties={},
            uuid=uuid,
            vector=vector,
        )
    objs = client.collection.get("Test").data.get()
    assert len(objs) == 1


@pytest.mark.skip()
def test_delete_objects(client: weaviate.Client):
    with client.batch as batch:
        batch.add_data_object(data_object={"name": "one"}, class_name="Test")
        batch.add_data_object(data_object={"name": "two"}, class_name="test")
        batch.add_data_object(data_object={"name": "three"}, class_name="Test")
        batch.add_data_object(data_object={"name": "four"}, class_name="test")
        batch.add_data_object(data_object={"name": "five"}, class_name="Test")

    with client.batch as batch:
        batch.delete_objects(
            "Test",
            where={
                "path": ["name"],
                "operator": "Equal",
                "valueText": "one",
            },
        )
    res = client.data_object.get()
    names = [obj["properties"]["name"] for obj in res["objects"]]
    assert "one" not in names

    with client.batch as batch:
        batch.delete_objects(
            "test",
            where={
                "path": ["name"],
                "operator": "ContainsAny",
                "valueTextArray": ["two", "three"],
            },
        )
    res = client.data_object.get()
    names = [obj["properties"]["name"] for obj in res["objects"]]
    assert "two" not in names
    assert "three" not in names

    with client.batch as batch:
        batch.delete_objects(
            "Test",
            where={
                "path": ["name"],
                "operator": "ContainsAll",
                "valueTextArray": ["four", "five"],
            },
        )
    res = client.data_object.get()
    names = [obj["properties"]["name"] for obj in res["objects"]]
    assert "four" in names
    assert "five" in names

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

    with client.collection.batch as batch:
        batch.add_object(
            properties={},
            class_name="Test",
            uuid=from_object_uuid,
        )
        batch.add_object(
            properties={},
            class_name="Test",
            uuid=to_object_uuid,
        )
        batch.add_reference(
            from_object_uuid=from_object_uuid,
            from_object_class_name="Test",
            from_property_name="test",
            to_object_uuid=to_object_uuid,
            to_object_class_name=to_object_class_name,
        )
    objs = client.collection.get("Test").data.get()
    obj = client.collection.get("Test").data.get_by_id(from_object_uuid)
    assert len(objs) == 2
    assert isinstance(obj.properties["test"][0]["beacon"], str)


def test_add_object_batch_with_tenant():
    client = weaviate.Client(
        "http://localhost:8080", additional_config=Config(grpc_port_experimental=50051)
    )

    # create two classes and add 5 tenants each
    class_names = ["BatchTestMultiTenant1", "BatchTestMultiTenant2"]
    for name in class_names:
        client.collection.create(
            CollectionConfig(
                name=name,
                properties=[
                    Property(name="tenantAsProp", data_type=DataType.TEXT),
                ],
                multi_tenancy_config=MultiTenancyConfig(enabled=True),
            )
        )
        client.collection.get(name).tenants.add([Tenant(name="tenant" + str(i)) for i in range(5)])

    nr_objects = 100
    objects = []
    with client.collection.batch as batch:
        for i in range(nr_objects):
            obj_uuid = uuid.uuid4()
            objects.append((obj_uuid, class_names[i % 2], "tenant" + str(i % 5)))
            batch.add_object(
                class_name=class_names[i % 2],
                tenant="tenant" + str(i % 5),
                properties={"tenantAsProp": "tenant" + str(i % 5)},
                uuid=obj_uuid,
            )

    for obj in objects:
        retObj = client.collection.get(obj[1]).with_tenant(obj[2]).data.get_by_id(obj[0])
        assert retObj.properties["tenantAsProp"] == obj[2]

    # test batch delete with wrong tenant id
    # with client.batch() as batch:
    #     batch.delete_objects(
    #         class_name=objects[0][1],
    #         where={
    #             "path": ["tenantAsProp"],
    #             "operator": "Equal",
    #             "valueString": objects[0][2],
    #         },
    #         tenant=objects[1][2],
    #     )

    #     retObj = client.data_object.get_by_id(
    #         objects[0][0], class_name=objects[0][1], tenant=objects[0][2]
    #     )
    #     assert retObj["properties"]["tenantAsProp"] == objects[0][2]

    # # test batch delete with correct tenant id
    # with client.batch() as batch:
    #     batch.delete_objects(
    #         class_name=objects[0][1],
    #         where={
    #             "path": ["tenantAsProp"],
    #             "operator": "Equal",
    #             "valueString": objects[0][2],
    #         },
    #         tenant=objects[0][2],
    #     )

    #     retObj = client.data_object.get_by_id(
    #         objects[0][0], class_name=objects[0][1], tenant=objects[0][2]
    #     )
    #     assert retObj is None

    for name in class_names:
        client.collection.delete(name)


def test_add_ref_batch_with_tenant():
    client = weaviate.Client(
        "http://localhost:8080", additional_config=Config(grpc_port_experimental=50051)
    )
    client.schema.delete_all()

    # create two classes and add 5 tenants each
    class_names = ["BatchRefTestMultiTenant0", "BatchRefTestMultiTenant1"]
    client.collection.create(
        CollectionConfig(
            name=class_names[0],
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
        )
    )

    client.collection.create(
        CollectionConfig(
            name=class_names[1],
            properties=[
                Property(name="tenantAsProp", data_type=DataType.TEXT),
                ReferenceProperty(name="ref", target_collection=class_names[0]),
            ],
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
        )
    )

    for name in class_names:
        client.collection.get(name).tenants.add([Tenant(name="tenant" + str(i)) for i in range(5)])

    nr_objects = 100
    objects_class0 = []
    objects_class1 = []
    with client.collection.batch as batch:
        for i in range(nr_objects):
            tenant = "tenant" + str(i % 5)
            obj_uuid0 = uuid.uuid4()
            objects_class0.append(obj_uuid0)
            batch.add_object(
                class_name=class_names[0], tenant=tenant, properties={}, uuid=obj_uuid0
            )

            obj_uuid1 = uuid.uuid4()
            objects_class1.append((obj_uuid1, "tenant" + str(i % 5)))
            batch.add_object(
                class_name=class_names[1],
                tenant=tenant,
                properties={"tenantAsProp": tenant},
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
        ret_obj = client.collection.get(class_names[1]).with_tenant(obj[1]).data.get_by_id(obj[0])
        assert ret_obj.properties["tenantAsProp"] == obj[1]
        assert (
            ret_obj.properties["ref"][0]["beacon"]
            == f"weaviate://localhost/{class_names[0]}/{objects_class0[i]}"
        )

    for name in reversed(class_names):
        client.collection.delete(name)


def test_add_ten_thousand_data_objects(client: weaviate.Client):
    """Test adding one million data objects"""
    nr_objects = 10000
    client.collection.batch.configure(num_workers=4)
    with client.collection.batch as batch:
        for i in range(nr_objects):
            batch.add_object(
                class_name="Test",
                properties={"name": "test" + str(i)},
            )
    objs = client.collection.get("Test").data.get(limit=nr_objects)
    assert len(objs) == nr_objects
    client.collection.delete("Test")


def test_add_bad_prop(client: weaviate.Client):
    """Test adding a data object with a bad property"""

    class WrappedObjectsBatchRequest(ObjectsBatchRequest):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.returns = []

        def _add_failed_objects_from_response(
            self,
            return_: _BatchObjectReturn,
            errors_to_exclude: List[str] | None = None,
            errors_to_include: List[str] | None = None,
        ) -> None:
            self.returns.append(return_)
            return super()._add_failed_objects_from_response(
                return_, errors_to_exclude, errors_to_include
            )

    wrapper = WrappedObjectsBatchRequest()
    with client.collection.batch as batch:
        batch.__batch_objects = wrapper
        batch.add_object(
            class_name="Test",
            properties={"bad": "test"},
        )
    assert len(wrapper.returns) == 1
