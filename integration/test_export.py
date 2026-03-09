import time
import uuid
from typing import Generator, List, Union

import pytest
from _pytest.fixtures import SubRequest

import weaviate
from weaviate.auth import Auth
from weaviate.collections.classes.config import DataType, Property
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.export.export import (
    ExportFileFormat,
    ExportStatus,
    ExportStorage,
)

from .conftest import _sanitize_collection_name

RBAC_PORTS = (8093, 50065)
RBAC_AUTH_CREDS = Auth.api_key("admin-key")

pytestmark = pytest.mark.xdist_group(name="export")

BACKEND = ExportStorage.FILESYSTEM

COLLECTION_NAME = "ExportTestCollection"

OBJECT_PROPS = [{"title": f"object {i}", "count": i} for i in range(5)]

OBJECT_IDS = [
    "fd34ccf4-1a2a-47ad-8446-231839366c3f",
    "2653442b-05d8-4fa3-b46a-d4a152eb63bc",
    "55374edb-17de-487f-86cb-9a9fbc30823f",
    "124ff6aa-597f-44d0-8c13-62fbb1e66888",
    "f787386e-7d1c-481f-b8c3-3dbfd8bbad85",
]


@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local(
        port=RBAC_PORTS[0], grpc_port=RBAC_PORTS[1], auth_credentials=RBAC_AUTH_CREDS
    )
    client.collections.delete(COLLECTION_NAME)

    col = client.collections.create(
        name=COLLECTION_NAME,
        properties=[
            Property(name="title", data_type=DataType.TEXT),
            Property(name="count", data_type=DataType.INT),
        ],
    )
    for i, props in enumerate(OBJECT_PROPS):
        col.data.insert(properties=props, uuid=OBJECT_IDS[i])

    yield client
    client.collections.delete(COLLECTION_NAME)
    client.close()


def unique_export_id(name: str) -> str:
    """Generate a unique export ID based on the test name."""
    name = _sanitize_collection_name(name)
    random_part = str(uuid.uuid4()).replace("-", "")[:12]
    return name + random_part


def test_create_export_with_waiting(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    """Create an export with wait_for_completion=True."""
    export_id = unique_export_id(request.node.name)

    resp = client.export.create(
        export_id=export_id,
        backend=BACKEND,
        include_collections=[COLLECTION_NAME],
        wait_for_completion=True,
    )
    assert resp.status == ExportStatus.SUCCESS
    assert COLLECTION_NAME in resp.collections


def test_create_export_without_waiting(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Create an export without waiting, then poll status."""
    export_id = unique_export_id(request.node.name)

    resp = client.export.create(
        export_id=export_id,
        backend=BACKEND,
        include_collections=[COLLECTION_NAME],
    )
    assert resp.status in [ExportStatus.STARTED, ExportStatus.TRANSFERRING, ExportStatus.SUCCESS]

    # poll until done
    while True:
        status = client.export.get_status(export_id=export_id, backend=BACKEND)
        assert status.status in [
            ExportStatus.STARTED,
            ExportStatus.TRANSFERRING,
            ExportStatus.SUCCESS,
        ]
        if status.status == ExportStatus.SUCCESS:
            break
        time.sleep(0.1)

    assert status.export_id == export_id


def test_get_export_status(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    """Check status of a completed export."""
    export_id = unique_export_id(request.node.name)

    client.export.create(
        export_id=export_id,
        backend=BACKEND,
        include_collections=[COLLECTION_NAME],
        wait_for_completion=True,
    )

    status = client.export.get_status(export_id=export_id, backend=BACKEND)
    assert status.status == ExportStatus.SUCCESS
    assert status.export_id == export_id
    assert status.backend == BACKEND.value


def test_create_export_with_parquet_format(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Create an export explicitly specifying parquet format."""
    export_id = unique_export_id(request.node.name)

    resp = client.export.create(
        export_id=export_id,
        backend=BACKEND,
        file_format=ExportFileFormat.PARQUET,
        include_collections=[COLLECTION_NAME],
        wait_for_completion=True,
    )
    assert resp.status == ExportStatus.SUCCESS


@pytest.mark.parametrize("include", [[COLLECTION_NAME], COLLECTION_NAME])
def test_create_export_include_as_str_and_list(
    client: weaviate.WeaviateClient, include: Union[str, List[str]], request: SubRequest
) -> None:
    """Verify include_collections accepts both str and list."""
    export_id = unique_export_id(request.node.name)

    resp = client.export.create(
        export_id=export_id,
        backend=BACKEND,
        include_collections=include,
        wait_for_completion=True,
    )
    assert resp.status == ExportStatus.SUCCESS
    assert COLLECTION_NAME in resp.collections


def test_cancel_export(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    """Cancel a running export."""
    export_id = unique_export_id(request.node.name)

    resp = client.export.create(
        export_id=export_id,
        backend=BACKEND,
        include_collections=[COLLECTION_NAME],
    )
    assert resp.status in [ExportStatus.STARTED, ExportStatus.TRANSFERRING, ExportStatus.SUCCESS]

    result = client.export.cancel(export_id=export_id, backend=BACKEND)
    assert result is True

    # verify it's cancelled or already completed (race condition)
    start = time.time()
    while time.time() - start < 5:
        status = client.export.get_status(export_id=export_id, backend=BACKEND)
        if status.status in [ExportStatus.CANCELLED, ExportStatus.SUCCESS]:
            break
        time.sleep(0.1)
    assert status.status in [ExportStatus.CANCELLED, ExportStatus.SUCCESS]


def test_fail_on_non_existing_collection(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Fail export on non-existing collection."""
    export_id = unique_export_id(request.node.name)
    with pytest.raises(UnexpectedStatusCodeException):
        client.export.create(
            export_id=export_id,
            backend=BACKEND,
            include_collections=["NonExistingCollection"],
            wait_for_completion=True,
        )


def test_fail_on_both_include_and_exclude(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Fail when both include and exclude collections are set."""
    export_id = unique_export_id(request.node.name)
    with pytest.raises(TypeError):
        client.export.create(
            export_id=export_id,
            backend=BACKEND,
            include_collections=COLLECTION_NAME,
            exclude_collections="SomeOther",
        )


def test_fail_status_for_non_existing_export(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Fail checking status for non-existing export."""
    export_id = unique_export_id(request.node.name)
    with pytest.raises(UnexpectedStatusCodeException):
        client.export.get_status(export_id=export_id, backend=BACKEND)
