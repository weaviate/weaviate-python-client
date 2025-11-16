import datetime
import pathlib
import time
import uuid
from typing import Generator, List, Optional, Union

import pytest
from _pytest.fixtures import SubRequest

import weaviate
import weaviate.classes as wvc
from weaviate.auth import Auth
from weaviate.backup.backup import (
    BackupCompressionLevel,
    BackupConfigCreate,
    BackupConfigRestore,
    BackupStatus,
    BackupStorage,
)
from weaviate.collections.classes.config import DataType, Property, ReferenceProperty
from weaviate.exceptions import (
    BackupFailedException,
    UnexpectedStatusCodeException,
)

from .conftest import ClientFactory, _sanitize_collection_name

RBAC_PORTS = (8093, 50065)
RBAC_AUTH_CREDS = Auth.api_key("admin-key")

pytestmark = pytest.mark.xdist_group(name="backup")

BACKEND = BackupStorage.FILESYSTEM

PARAGRAPHS_IDS = [
    "fd34ccf4-1a2a-47ad-8446-231839366c3f",
    "2653442b-05d8-4fa3-b46a-d4a152eb63bc",
    "55374edb-17de-487f-86cb-9a9fbc30823f",
    "124ff6aa-597f-44d0-8c13-62fbb1e66888",
    "f787386e-7d1c-481f-b8c3-3dbfd8bbad85",
]


PARAGRAPHS_PROPS = [
    {"contents": "paragraph 1"},
    {"contents": "paragraph 2"},
    {"contents": "paragraph 3"},
    {"contents": "paragraph 4"},
    {"contents": "paragraph 5"},
]

ARTICLES_IDS = [
    "2fd68cbc-21ff-4e19-aaef-62531dade974",
    "7ea3f7b8-65fd-4318-a842-ae9ba38ffdca",
    "769a4280-4b85-4e67-b685-07796c49a764",
    "97fcc234-fd16-4a40-82bb-d614e9bddf8b",
    "3fa435d3-6ab2-489d-abed-c25ec526c9f4",
]

ARTICLES_PROPS = [
    {
        "title": "article a",
        "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "title": "article b",
        "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "title": "article c",
        "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "title": "article d",
        "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    {
        "title": "article e",
        "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
]
CLASSES = ["Paragraph", "Article"]


@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local(
        port=RBAC_PORTS[0], grpc_port=RBAC_PORTS[1], auth_credentials=RBAC_AUTH_CREDS
    )
    client.collections.delete(CLASSES)

    col_para = client.collections.create(
        name="Paragraph",
        properties=[Property(name="contents", data_type=DataType.TEXT)],
        references=[
            ReferenceProperty(name="hasParagraphs", target_collection="Paragraph"),
        ],
    )
    for i, para in enumerate(PARAGRAPHS_PROPS):
        col_para.data.insert(properties=para, uuid=PARAGRAPHS_IDS[i])

    col_articles = client.collections.create(
        name="Article",
        properties=[
            Property(name="title", data_type=DataType.TEXT),
            Property(name="datePublished", data_type=DataType.DATE),
        ],
        references=[
            ReferenceProperty(name="hasParagraphs", target_collection="Paragraph"),
        ],
    )

    for i, art in enumerate(ARTICLES_PROPS):
        col_articles.data.insert(properties=art, uuid=ARTICLES_IDS[i])
        col_articles.data.reference_add(
            from_uuid=ARTICLES_IDS[i],
            from_property="hasParagraphs",
            to=PARAGRAPHS_IDS[i],
        )
    yield client
    client.collections.delete("Paragraph")
    client.collections.delete("Article")


def unique_backup_id(name: str) -> str:
    """Generate a unique backup ID based on the test name."""
    name = _sanitize_collection_name(name)
    random_part = str(uuid.uuid4()).replace("-", "")[:12]
    return name + random_part


def test_create_and_restore_backup_with_waiting(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Create and restore backup with waiting."""
    backup_id = unique_backup_id(request.node.name)

    # create backup
    classes = ["Article", "Paragraph"]
    resp = client.backup.create(
        backup_id=backup_id,
        backend=BACKEND,
        wait_for_completion=True,
        include_collections=CLASSES,
    )
    assert resp.status == BackupStatus.SUCCESS
    for cls in classes:
        assert cls in resp.collections

    assert len(client.collections.use("Article")) == len(ARTICLES_IDS)
    assert len(client.collections.use("Paragraph")) == len(PARAGRAPHS_IDS)

    # check create status
    create_status = client.backup.get_create_status(backup_id, BACKEND)
    assert create_status.status == BackupStatus.SUCCESS
    assert create_status.backup_id.lower() == backup_id.lower()

    # remove existing class
    client.collections.delete("Article")
    client.collections.delete("Paragraph")

    # restore backup
    restore = client.backup.restore(
        backup_id=backup_id,
        backend=BACKEND,
        wait_for_completion=True,
        include_collections=CLASSES,
    )
    assert restore.status == BackupStatus.SUCCESS
    for cls in classes:
        assert cls in resp.collections

    # # check data exists again
    assert len(client.collections.use("Article")) == len(ARTICLES_IDS)
    assert len(client.collections.use("Paragraph")) == len(PARAGRAPHS_IDS)

    # check restore status
    restore_status = client.backup.get_restore_status(backup_id, BACKEND)
    assert restore_status.status == BackupStatus.SUCCESS


@pytest.mark.parametrize("include", [["Article"], "Article"])
def test_create_and_restore_backup_without_waiting(
    client: weaviate.WeaviateClient, include: Union[str, List[str]], request: SubRequest
) -> None:
    """Create and restore backup without waiting."""
    backup_id = unique_backup_id(request.node.name)
    include_as_list = sorted(include) if isinstance(include, list) else [include]

    resp = client.backup.create(backup_id=backup_id, include_collections=include, backend=BACKEND)
    assert resp.status == BackupStatus.STARTED
    assert sorted(resp.collections) == include_as_list

    # wait until created
    while True:
        create_status = client.backup.get_create_status(backup_id, BACKEND)
        assert create_status.status in [
            BackupStatus.SUCCESS,
            BackupStatus.TRANSFERRED,
            BackupStatus.TRANSFERRING,
            BackupStatus.STARTED,
        ]
        if create_status.status == BackupStatus.SUCCESS:
            break
        time.sleep(0.1)

    # check data still exists, then remove existing class
    assert len(client.collections.use("Article")) == len(ARTICLES_IDS)
    client.collections.delete(name="Article")

    # restore backup
    restore = client.backup.restore(
        backup_id=backup_id,
        include_collections=include,
        backend=BACKEND,
    )
    assert restore.status == BackupStatus.STARTED
    assert sorted(restore.collections) == include_as_list

    # wait until restored
    while True:
        restore_status = client.backup.get_restore_status(backup_id, BACKEND)
        assert restore_status.status in [
            BackupStatus.SUCCESS,
            BackupStatus.TRANSFERRED,
            BackupStatus.TRANSFERRING,
            BackupStatus.STARTED,
        ]
        if restore_status.status == BackupStatus.SUCCESS:
            break
        time.sleep(0.1)

    # check data exists again
    assert len(client.collections.use("Article")) == len(ARTICLES_IDS)


def test_create_and_restore_1_of_2_classes(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Create and restore 1 of 2 classes."""
    backup_id = unique_backup_id(request.node.name)

    # check data exists
    assert len(client.collections.use("Article")) == len(ARTICLES_IDS)

    # create backup
    include = ["Article"]
    create = client.backup.create(
        backup_id=backup_id,
        include_collections=include,
        backend=BACKEND,
        wait_for_completion=True,
    )
    assert create.status == BackupStatus.SUCCESS

    status_create = client.backup.get_create_status(backup_id, BACKEND)
    assert status_create.status == BackupStatus.SUCCESS

    # check data still exists and then remove existing class
    assert len(client.collections.use("Article")) == len(ARTICLES_IDS)
    client.collections.delete(name="Article")

    # restore backup
    restore = client.backup.restore(
        backup_id=backup_id,
        include_collections=include,
        backend=BACKEND,
        wait_for_completion=True,
    )
    assert restore.status == BackupStatus.SUCCESS

    # check data exists again
    assert len(client.collections.use("Article")) == len(ARTICLES_IDS)

    # check restore status
    restore_status = client.backup.get_restore_status(backup_id, BACKEND)
    assert restore_status.status == BackupStatus.SUCCESS


def test_fail_on_non_existing_class(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    """Fail backup functions on non-existing class."""
    backup_id = unique_backup_id(request.node.name)
    class_name = "NonExistingClass"
    for func in [client.backup.create, client.backup.restore]:
        with pytest.raises(UnexpectedStatusCodeException) as excinfo:
            func(backup_id=backup_id, backend=BACKEND, include_collections=class_name)
            assert class_name in str(excinfo.value)
            assert "422" in str(excinfo.value)


def test_fail_restoring_backup_for_existing_class(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Fail restoring backup for existing class."""
    backup_id = unique_backup_id(request.node.name)
    class_name = ["Article"]
    create = client.backup.create(
        backup_id=backup_id,
        include_collections=class_name,
        backend=BACKEND,
        wait_for_completion=True,
    )
    assert create.status == BackupStatus.SUCCESS

    # fail restore
    with pytest.raises(BackupFailedException) as excinfo:
        client.backup.restore(
            backup_id=backup_id,
            include_collections=class_name,
            backend=BACKEND,
            wait_for_completion=True,
        )
        assert class_name[0] in str(excinfo.value)
        assert "already exists" in str(excinfo.value)


def test_fail_creating_existing_backup(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Fail creating existing backup."""
    backup_id = unique_backup_id(request.node.name)
    class_name = ["Article"]
    create = client.backup.create(
        backup_id=backup_id,
        include_collections=class_name,
        backend=BACKEND,
        wait_for_completion=True,
    )
    assert create.status == BackupStatus.SUCCESS

    # fail create
    with pytest.raises(UnexpectedStatusCodeException) as excinfo:
        client.backup.create(
            backup_id=backup_id,
            include_collections=class_name,
            backend=BACKEND,
            wait_for_completion=True,
        )
        assert backup_id in str(excinfo.value)
        assert "422" in str(excinfo.value)


def test_fail_restoring_non_existing_backup(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Fail restoring non-existing backup."""
    backup_id = unique_backup_id(request.node.name)
    with pytest.raises(UnexpectedStatusCodeException) as excinfo:
        client.backup.restore(backup_id=backup_id, backend=BACKEND, wait_for_completion=True)
        assert backup_id in str(excinfo.value)
        assert "404" in str(excinfo.value)


def test_fail_checking_status_for_non_existing_restore(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Fail checking restore status for non-existing restore."""
    backup_id = unique_backup_id(request.node.name)
    for func in [client.backup.get_restore_status, client.backup.get_create_status]:
        with pytest.raises(UnexpectedStatusCodeException) as excinfo:
            func(
                backup_id=backup_id,
                backend=BACKEND,
            )
            assert backup_id in str(excinfo)
            assert "404" in str(excinfo)


def test_fail_creating_backup_for_both_include_and_exclude_classes(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    """Fail creating backup for both include and exclude classes."""
    backup_id = unique_backup_id(request.node.name)

    for func in [client.backup.create, client.backup.restore]:
        with pytest.raises(TypeError) as excinfo:
            include = "Article"
            exclude = "Paragraph"
            func(
                backup_id=backup_id,
                include_collections=include,
                exclude_collections=exclude,
                backend=BACKEND,
                wait_for_completion=True,
            )
            assert "Either 'include_classes' OR 'exclude_classes' can be set, not both" in str(
                excinfo.value
            )


@pytest.mark.parametrize("dynamic_backup_location", [False, True])
def test_backup_and_restore_with_dynamic_location(
    client: weaviate.WeaviateClient,
    dynamic_backup_location: bool,
    tmp_path: pathlib.Path,
    request: SubRequest,
) -> None:
    backup_id = unique_backup_id(request.node.name)

    conf_create: Optional[wvc.backup.BackupConfigCreate] = None
    conf_restore: Optional[wvc.backup.BackupConfigRestore] = None
    backup_location: Optional[wvc.backup.BackupLocationType] = None
    if dynamic_backup_location:
        if client._connection._weaviate_version.is_lower_than(1, 27, 2):
            pytest.skip("Cancel backups is only supported from 1.27.2")

        backup_location = wvc.backup.BackupLocation.FileSystem(path=str(tmp_path))

    article = client.collections.use("Article")

    # create backup
    create = article.backup.create(
        backup_id=backup_id,
        backend=BACKEND,
        wait_for_completion=True,
        config=conf_create,
        backup_location=backup_location,
    )
    assert create.status == BackupStatus.SUCCESS

    assert len(article) == len(ARTICLES_IDS)

    # check create status
    create_status = article.backup.get_create_status(
        backup_id=backup_id, backend=BACKEND, backup_location=backup_location
    )
    assert create_status.status == BackupStatus.SUCCESS

    # remove existing class
    client.collections.delete("Article")

    # restore backup
    restore = article.backup.restore(
        backup_id=backup_id,
        backend=BACKEND,
        wait_for_completion=True,
        config=conf_restore,
        backup_location=backup_location,
    )
    assert restore.status == BackupStatus.SUCCESS

    # # check data exists again
    assert len(article) == len(ARTICLES_IDS)

    # check restore status
    restore_status = article.backup.get_restore_status(backup_id, BACKEND, backup_location)
    assert restore_status.status == BackupStatus.SUCCESS


def test_backup_and_restore_with_collection_and_config_1_24_x(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    if client._connection._weaviate_version.is_lower_than(1, 25, 0):
        pytest.skip("Backup config is only supported from Weaviate 1.25.0")

    backup_id = unique_backup_id(request.node.name)

    article = client.collections.use("Article")

    # create backup
    create = article.backup.create(
        backup_id=backup_id,
        backend=BACKEND,
        wait_for_completion=True,
        config=BackupConfigCreate(
            cpu_percentage=60,
            chunk_size=256,
            compression_level=BackupCompressionLevel.BEST_SPEED,
        ),
    )
    assert create.status == BackupStatus.SUCCESS

    assert len(article) == len(ARTICLES_IDS)

    # check create status
    create_status = article.backup.get_create_status(backup_id, BACKEND)
    assert create_status.status == BackupStatus.SUCCESS

    # remove existing class
    client.collections.delete("Article")

    # restore backup
    restore = article.backup.restore(
        backup_id=backup_id,
        backend=BACKEND,
        wait_for_completion=True,
        config=BackupConfigRestore(cpu_percentage=70),
    )
    assert restore.status == BackupStatus.SUCCESS

    # # check data exists again
    assert len(article) == len(ARTICLES_IDS)

    # check restore status
    restore_status = article.backup.get_restore_status(backup_id, BACKEND)
    assert restore_status.status == BackupStatus.SUCCESS


@pytest.mark.parametrize("dynamic_backup_location", [False, True])
def test_cancel_backup(
    client: weaviate.WeaviateClient,
    dynamic_backup_location: bool,
    tmp_path: pathlib.Path,
    request: SubRequest,
) -> None:
    """Cancel backup without waiting."""
    backup_id = unique_backup_id(request.node.name)
    if client._connection._weaviate_version.is_lower_than(1, 24, 25):
        pytest.skip("Cancel backups is only supported from 1.24.25")

    backup_location: Optional[wvc.backup.BackupLocationType] = None
    if dynamic_backup_location:
        if client._connection._weaviate_version.is_lower_than(1, 27, 2):
            pytest.skip("Cancel backups is only supported from 1.27.2")

        backup_location = wvc.backup.BackupLocation.FileSystem(path=str(tmp_path))

    resp = client.backup.create(
        backup_id=backup_id,
        backend=BACKEND,
        backup_location=backup_location,
        include_collections=CLASSES,
    )
    assert resp.status == BackupStatus.STARTED

    assert client.backup.cancel(
        backup_id=backup_id, backend=BACKEND, backup_location=backup_location
    )

    # async process
    start = time.time()
    while time.time() - start < 5:
        status_resp = client.backup.get_create_status(
            backup_id=backup_id, backend=BACKEND, backup_location=backup_location
        )
        if status_resp.status == BackupStatus.CANCELED:
            break
        time.sleep(0.1)
    status_resp = client.backup.get_create_status(
        backup_id=backup_id, backend=BACKEND, backup_location=backup_location
    )
    # there can be a race between the cancel and the backup completion
    assert status_resp.status == BackupStatus.CANCELED or status_resp.status == BackupStatus.SUCCESS


def test_backup_and_restore_with_roles_and_users(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    backup_id = unique_backup_id(request.node.name)
    client = client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS)
    if client._connection._weaviate_version.is_lower_than(1, 30, 10):
        pytest.skip("User and roles are only supported from Weaviate 1.30.10")

    name = _sanitize_collection_name(request.node.fspath.basename + "_" + request.node.name)
    client.collections.delete(name)
    client.collections.create(name=name)

    client.users.db.delete(user_id=name)
    client.users.db.create(user_id=name)

    client.roles.delete(role_name=name)
    client.roles.create(
        role_name=name,
        permissions=wvc.rbac.Permissions.collections(collection="*", create_collection=True),
    )

    resp = client.backup.create(
        backup_id=backup_id,
        backend=BACKEND,
        wait_for_completion=True,
        include_collections=[name],
    )
    assert resp.status == BackupStatus.SUCCESS

    client.users.db.delete(user_id=name)
    client.roles.delete(role_name=name)
    client.collections.delete(name)
    assert client.users.db.get(user_id=name) is None
    assert client.roles.get(role_name=name) is None

    resp = client.backup.restore(
        backup_id=backup_id,
        backend=BACKEND,
        wait_for_completion=True,
        roles_restore="all",
        users_restore="all",
    )

    assert client.users.db.get(user_id=name) is not None
    assert client.roles.get(role_name=name) is not None


def test_list_backup(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    """List all backups."""
    backup_id = unique_backup_id(request.node.name)
    if client._connection._weaviate_version.is_lower_than(1, 30, 0):
        pytest.skip("List backups is only supported from 1.30.0")

    resp = client.backup.create(backup_id=backup_id, backend=BACKEND)
    assert resp.status == BackupStatus.STARTED

    backups = client.backup.list_backups(backend=BACKEND)
    assert backup_id.lower() in [b.backup_id.lower() for b in backups]

    # wait until created
    while True:
        create_status = client.backup.get_create_status(backup_id, BACKEND)
        assert create_status.status in [
            BackupStatus.SUCCESS,
            BackupStatus.TRANSFERRED,
            BackupStatus.TRANSFERRING,
            BackupStatus.STARTED,
        ]
        if create_status.status == BackupStatus.SUCCESS:
            break
        time.sleep(0.1)


def test_list_backup_ascending_order(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    """List all backups in ascending order."""
    backup_id = unique_backup_id(request.node.name)
    if client._connection._weaviate_version.is_lower_than(1, 33, 2):
        pytest.skip("List backups sorting is only supported from 1.33.2")

    resp = client.backup.create(backup_id=backup_id, backend=BACKEND)
    assert resp.status == BackupStatus.STARTED

    while True:
        create_status = client.backup.get_create_status(backup_id, BACKEND)
        assert create_status.status in [
            BackupStatus.SUCCESS,
            BackupStatus.TRANSFERRED,
            BackupStatus.TRANSFERRING,
            BackupStatus.STARTED,
        ]
        if create_status.status == BackupStatus.SUCCESS:
            break
        time.sleep(0.1)

    backups = client.backup.list_backups(backend=BACKEND, sort_by_starting_time_asc=True)
    assert backup_id.lower() in [b.backup_id.lower() for b in backups]

    assert sorted(backups, key=lambda b: b.started_at or b.backup_id) == backups


@pytest.fixture
def artist_alias(client: weaviate.WeaviateClient) -> Generator[str, None, None]:
    if client._connection._weaviate_version.is_lower_than(1, 32, 0):
        pytest.skip("overwriteAlias is only supported from 1.33.0 onwards")

    client.alias.create(target_collection="Article", alias_name="Literature")
    yield "Literature"
    client.alias.delete(alias_name="Literature")


def test_overwrite_alias_true(
    client: weaviate.WeaviateClient, request: SubRequest, artist_alias: str
) -> None:
    """Restore backups with overwrite=true."""
    backup_id = unique_backup_id(request.node.name)
    client.backup.create(
        backup_id=backup_id,
        backend=BACKEND,
        include_collections=["Article"],
        wait_for_completion=True,
    )

    client.collections.delete("Article")
    client.alias.update(alias_name=artist_alias, new_target_collection="Paragraph")

    client.backup.restore(
        backup_id=backup_id,
        backend=BACKEND,
        include_collections=["Article"],
        wait_for_completion=True,
        overwrite_alias=True,
    )

    literature = client.alias.get(alias_name="Literature")
    assert literature is not None, "expect alias exists"
    assert literature.collection == "Article", "alias must point to the original collection"


# This test has been disabled temporarily until the behaviour of this scenario is clarified.
# It worked in version 1.33.0-rc.1, but broken in version 1.33.0+
# def test_overwrite_alias_false(
#     client: weaviate.WeaviateClient, request: SubRequest, artist_alias: str
# ) -> None:
#     """Restore backups with overwrite=false (conflict)."""
#     backup_id = unique_backup_id(request.node.name)

#     client.backup.create(
#         backup_id=backup_id,
#         backend=BACKEND,
#         include_collections=["Article"],
#         wait_for_completion=True,
#     )

#     client.collections.delete("Article")
#     client.alias.update(alias_name=artist_alias, new_target_collection="Paragraph")

#     with pytest.raises(BackupFailedError) as err:
#         client.backup.restore(
#             backup_id=backup_id,
#             backend=BACKEND,
#             include_collections=["Article"],
#             wait_for_completion=True,
#             overwrite_alias=False,
#         )
#     assert "alias already exists" in str(err)
