from typing import Optional

import pytest
import requests

import weaviate
from weaviate import Tenant, TenantActivityStatus


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    yield client
    client.schema.delete_all()


@pytest.mark.parametrize("replicationFactor", [None, 1])
def test_create_class_with_implicit_and_explicit_replication_factor(
    client: weaviate.Client, replicationFactor: Optional[int]
):
    single_class = {
        "class": "Barbecue",
        "description": "Barbecue or BBQ where meat and vegetables get grilled",
        "properties": [
            {
                "dataType": ["string"],
                "description": "how hot is the BBQ in C",
                "name": "heat",
            },
        ],
    }
    if replicationFactor is None:
        expected_factor = 1
    else:
        expected_factor = replicationFactor
        single_class["replicationConfig"] = {
            "factor": replicationFactor,
        }

    client.schema.create_class(single_class)
    created_class = client.schema.get("Barbecue")
    assert created_class["class"] == "Barbecue"
    assert created_class["replicationConfig"]["factor"] == expected_factor

    client.schema.delete_class("Barbecue")


@pytest.mark.parametrize("data_type", ["uuid", "uuid[]"])
def test_uuid_datatype(client: weaviate.Client, data_type: str):
    single_class = {"class": "UuidTest", "properties": [{"dataType": [data_type], "name": "heat"}]}

    client.schema.create_class(single_class)
    created_class = client.schema.get("uuidTest")
    assert created_class["class"] == "UuidTest"

    client.schema.delete_class("UuidTest")


@pytest.mark.parametrize("object_", ["object", "object[]"])
@pytest.mark.parametrize(
    "nested",
    [
        {
            "dataType": ["text"],
            "name": "name",
        },
        {"dataType": ["text[]"], "name": "names"},
        {"dataType": ["int"], "name": "age"},
        {"dataType": ["int[]"], "name": "ages"},
        {"dataType": ["number"], "name": "weight"},
        {"dataType": ["number[]"], "name": "weights"},
        {"dataType": ["boolean"], "name": "isAlive"},
        {"dataType": ["boolean[]"], "name": "areAlive"},
        {"dataType": ["date"], "name": "birthDate"},
        {"dataType": ["date[]"], "name": "birthDates"},
        {"dataType": ["uuid"], "name": "uuid"},
        {"dataType": ["uuid[]"], "name": "uuids"},
        {"dataType": ["blob"], "name": "blob"},
        {
            "dataType": ["object"],
            "name": "object",
            "nestedProperties": [{"dataType": ["text"], "name": "name"}],
        },
        {
            "dataType": ["object[]"],
            "name": "objects",
            "nestedProperties": [{"dataType": ["text"], "name": "name"}],
        },
    ],
)
def test_object_datatype(client: weaviate.Client, object_: str, nested: dict):
    single_class = {
        "class": "ObjectTest",
        "properties": [{"dataType": [object_], "name": "heat", "nestedProperties": [nested]}],
    }

    client.schema.create_class(single_class)
    created_class = client.schema.get("ObjectTest")
    assert created_class["class"] == "ObjectTest"

    client.schema.delete_class("ObjectTest")


@pytest.mark.parametrize("tokenization", ["word", "whitespace", "lowercase", "field"])
def test_tokenization(client: weaviate.Client, tokenization):
    single_class = {
        "class": "TokenTest",
        "properties": [{"dataType": ["text"], "name": "heat", "tokenization": tokenization}],
    }
    client.schema.create_class(single_class)
    created_class = client.schema.get("TokenTest")
    assert created_class["class"] == "TokenTest"

    client.schema.delete_class("TokenTest")


def test_class_exists(client: weaviate.Client):
    single_class = {"class": "Exists"}

    client.schema.create_class(single_class)
    assert client.schema.exists("Exists") is True
    assert client.schema.exists("DoesNotExists") is False

    client.schema.delete_class("Exists")
    assert client.schema.exists("Exists") is False


def test_schema_keys(client: weaviate.Client):
    single_class = {
        "class": "Author",
        "properties": [
            {
                "indexFilterable": False,
                "indexSearchable": False,
                "dataType": ["text"],
                "name": "name",
            }
        ],
    }
    client.schema.create_class(single_class)
    assert client.schema.exists("Author")


def test_class_tenants(client: weaviate.Client):
    class_name = "MultiTenancySchemaTest"
    uncap_class_name = "multiTenancySchemaTest"
    single_class = {"class": class_name, "multiTenancyConfig": {"enabled": True}}
    client.schema.delete_all()
    client.schema.create_class(single_class)
    assert client.schema.exists(class_name)

    tenants = [
        Tenant(name="Tenant1"),
        Tenant(name="Tenant2"),
        Tenant(name="Tenant3"),
        Tenant(name="Tenant4"),
    ]
    client.schema.add_class_tenants(class_name, tenants[:2])
    client.schema.add_class_tenants(uncap_class_name, tenants[2:])
    tenants_get = client.schema.get_class_tenants(class_name)
    assert len(tenants_get) == len(tenants)

    client.schema.remove_class_tenants(class_name, ["Tenant2", "Tenant4"])
    client.schema.remove_class_tenants(uncap_class_name, ["Tenant1"])
    tenants_get = client.schema.get_class_tenants(uncap_class_name)
    assert len(tenants_get) == 1


def test_update_schema_with_no_properties(client: weaviate.Client):
    single_class = {"class": "NoProperties"}

    requests.post("http://localhost:8080/v1/schema", json=single_class)
    assert client.schema.exists("NoProperties")

    client.schema.update_config("NoProperties", {"vectorIndexConfig": {"ef": 64}})
    assert client.schema.exists("NoProperties")

    client.schema.delete_class("NoProperties")
    assert client.schema.exists("NoProperties") is False


def test_class_tenants_activate_deactivate(client: weaviate.Client):
    class_name = "MultiTenancyActivateDeactivateSchemaTest"
    uncap_class_name = "multiTenancyActivateDeactivateSchemaTest"
    single_class = {"class": class_name, "multiTenancyConfig": {"enabled": True}}
    client.schema.delete_all()
    client.schema.create_class(single_class)
    assert client.schema.exists(class_name)

    tenants = [
        Tenant(name="Tenant1"),
        Tenant(activity_status=TenantActivityStatus.COLD, name="Tenant2"),
        Tenant(name="Tenant3"),
    ]
    client.schema.add_class_tenants(class_name, tenants)
    tenants_get = client.schema.get_class_tenants(class_name)
    assert len(tenants_get) == len(tenants)
    # below required because tenants are returned in random order by the server
    for tenant in tenants_get:
        if tenant.name == "Tenant1":
            assert tenant.activity_status == TenantActivityStatus.HOT
        elif tenant.name == "Tenant2":
            assert tenant.activity_status == TenantActivityStatus.COLD
        elif tenant.name == "Tenant3":
            assert tenant.activity_status == TenantActivityStatus.HOT
        else:
            raise AssertionError(f"Unexpected tenant: {tenant.name}")

    updated_tenants = [
        Tenant(activity_status=TenantActivityStatus.COLD, name="Tenant1"),
        Tenant(activity_status=TenantActivityStatus.HOT, name="Tenant2"),
    ]
    client.schema.update_class_tenants(class_name, updated_tenants)
    tenants_get = client.schema.get_class_tenants(class_name)
    assert len(tenants_get) == len(tenants)
    # below required because tenants are returned in random order by the server
    for tenant in tenants_get:
        if tenant.name == "Tenant1":
            assert tenant.activity_status == TenantActivityStatus.COLD
        elif tenant.name == "Tenant2":
            assert tenant.activity_status == TenantActivityStatus.HOT
        elif tenant.name == "Tenant3":
            assert tenant.activity_status == TenantActivityStatus.HOT
        else:
            raise AssertionError(f"Unexpected tenant: {tenant.name}")

    updated_tenants = [
        Tenant(activity_status=TenantActivityStatus.COLD, name="Tenant3"),
    ]
    client.schema.update_class_tenants(uncap_class_name, updated_tenants)
    tenants_get = client.schema.get_class_tenants(uncap_class_name)
    assert len(tenants_get) == len(tenants)
    # below required because tenants are returned in random order by the server
    for tenant in tenants_get:
        if tenant.name == "Tenant1":
            assert tenant.activity_status == TenantActivityStatus.COLD
        elif tenant.name == "Tenant2":
            assert tenant.activity_status == TenantActivityStatus.HOT
        elif tenant.name == "Tenant3":
            assert tenant.activity_status == TenantActivityStatus.COLD
        else:
            raise AssertionError(f"Unexpected tenant: {tenant.name}")
