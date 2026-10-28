import pytest

from integration.conftest import (
    AsyncClientFactory,
    AsyncCollectionFactory,
    ClientFactory,
    CollectionFactory,
)
from weaviate.classes.config import DataType, Property
from weaviate.classes.debug import DebugRESTObject
from weaviate.exceptions import UnexpectedStatusCodeError

# The /v1/tasks REST endpoint landed on weaviate-core's stable/v1.37 branch on 2026-06-29
# but isn't in every Docker image this suite's version matrix pins yet, so older builds
# still respond 501 "not yet implemented" rather than a real payload.
_DISTRIBUTED_TASKS_NOT_IMPLEMENTED = 501


def test_get_object_single_node(
    client_factory: ClientFactory, collection_factory: CollectionFactory
) -> None:
    client = client_factory()
    collection = collection_factory(properties=[Property(name="name", data_type=DataType.TEXT)])

    uuid = collection.data.insert({"name": "John Doe"})

    debug_obj = client.debug.get_object_over_rest(collection.name, uuid)
    assert debug_obj is not None
    assert isinstance(debug_obj, DebugRESTObject)
    assert str(debug_obj.uuid) == str(uuid)

    non_existant_uuid = "00000000-0000-0000-0000-000000000000"
    debug_obj = client.debug.get_object_over_rest(collection.name, non_existant_uuid)
    assert debug_obj is None


@pytest.mark.asyncio
async def test_get_object_single_node_async(
    async_client_factory: AsyncClientFactory, async_collection_factory: AsyncCollectionFactory
) -> None:
    client = await async_client_factory()
    collection = await async_collection_factory(
        properties=[Property(name="name", data_type=DataType.TEXT)]
    )

    uuid = await collection.data.insert({"name": "John Doe"})

    debug_obj = await client.debug.get_object_over_rest(collection.name, uuid)
    assert debug_obj is not None
    assert isinstance(debug_obj, DebugRESTObject)
    assert str(debug_obj.uuid) == str(uuid)

    non_existant_uuid = "00000000-0000-0000-0000-000000000000"
    debug_obj = await client.debug.get_object_over_rest(collection.name, non_existant_uuid)
    assert debug_obj is None


def test_get_object_multi_node(
    client_factory: ClientFactory, collection_factory: CollectionFactory
) -> None:
    client = client_factory(ports=(8087, 50058))
    collection = collection_factory(
        ports=(8087, 50058), properties=[Property(name="name", data_type=DataType.TEXT)]
    )

    uuid = collection.data.insert({"name": "John Doe"})

    for node_name in ["node1", "node2", "node3"]:
        debug_obj = client.debug.get_object_over_rest(collection.name, uuid, node_name=node_name)
        assert debug_obj is not None
        assert str(debug_obj.uuid) == str(uuid)


def test_list_tasks(client_factory: ClientFactory) -> None:
    client = client_factory()

    try:
        tasks = client.debug.list_tasks()
    except UnexpectedStatusCodeError as e:
        if e.status_code == _DISTRIBUTED_TASKS_NOT_IMPLEMENTED:
            pytest.skip("distributed tasks endpoint not yet implemented on this server build")
        raise

    assert isinstance(tasks, dict)


@pytest.mark.asyncio
async def test_list_tasks_async(async_client_factory: AsyncClientFactory) -> None:
    client = await async_client_factory()

    try:
        tasks = await client.debug.list_tasks()
    except UnexpectedStatusCodeError as e:
        if e.status_code == _DISTRIBUTED_TASKS_NOT_IMPLEMENTED:
            pytest.skip("distributed tasks endpoint not yet implemented on this server build")
        raise

    assert isinstance(tasks, dict)
