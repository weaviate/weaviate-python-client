import datetime
import time
from typing import Generator, List, Union

import pytest

import weaviate
from weaviate.backup.backup import BackupStatus, BackupStorage
from weaviate.collections.classes.config import DataType, Property, ReferenceProperty
from weaviate.exceptions import UnexpectedStatusCodeException, BackupFailedException

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


@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local()
    client.collections.delete("Paragraph")
    client.collections.delete("Article")

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


def _create_backup_id() -> str:
    return str(round(time.time_ns() * 1000))


def test_create_and_restore_backup_with_waiting(client: weaviate.WeaviateClient) -> None:
    """Create and restore backup with waiting."""
    backup_id = _create_backup_id()

    # create backup
    classes = ["Article", "Paragraph"]
    resp = client.backup.create(backup_id=backup_id, backend=BACKEND, wait_for_completion=True)
    assert resp.status == BackupStatus.SUCCESS
    for cls in classes:
        assert cls in resp.collections

    assert len(client.collections.get("Article")) == len(ARTICLES_IDS)
    assert len(client.collections.get("Paragraph")) == len(PARAGRAPHS_IDS)

    # check create status
    create_status = client.backup.get_create_status(backup_id, BACKEND)
    assert create_status.status == BackupStatus.SUCCESS

    # remove existing class
    client.collections.delete("Article")
    client.collections.delete("Paragraph")

    # restore backup
    restore = client.backup.restore(backup_id=backup_id, backend=BACKEND, wait_for_completion=True)
    assert restore.status == BackupStatus.SUCCESS
    for cls in classes:
        assert cls in resp.collections

    # # check data exists again
    assert len(client.collections.get("Article")) == len(ARTICLES_IDS)
    assert len(client.collections.get("Paragraph")) == len(PARAGRAPHS_IDS)

    # check restore status
    restore_status = client.backup.get_restore_status(backup_id, BACKEND)
    assert restore_status.status == BackupStatus.SUCCESS


@pytest.mark.parametrize("include", [["Article"], "Article"])
def test_create_and_restore_backup_without_waiting(
    client: weaviate.WeaviateClient, include: Union[str, List[str]]
) -> None:
    """Create and restore backup without waiting."""
    backup_id = _create_backup_id()
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
    assert len(client.collections.get("Article")) == len(ARTICLES_IDS)
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
    assert len(client.collections.get("Article")) == len(ARTICLES_IDS)


def test_create_and_restore_1_of_2_classes(client: weaviate.WeaviateClient) -> None:
    """Create and restore 1 of 2 classes."""
    backup_id = _create_backup_id()

    # check data exists
    assert len(client.collections.get("Article")) == len(ARTICLES_IDS)

    # create backup
    include = ["Article"]
    create = client.backup.create(
        backup_id=backup_id, include_collections=include, backend=BACKEND, wait_for_completion=True
    )
    assert create.status == BackupStatus.SUCCESS

    status_create = client.backup.get_create_status(backup_id, BACKEND)
    assert status_create.status == BackupStatus.SUCCESS

    # check data still exists and then remove existing class
    assert len(client.collections.get("Article")) == len(ARTICLES_IDS)
    client.collections.delete(name="Article")

    # restore backup
    restore = client.backup.restore(
        backup_id=backup_id, include_collections=include, backend=BACKEND, wait_for_completion=True
    )
    assert restore.status == BackupStatus.SUCCESS

    # check data exists again
    assert len(client.collections.get("Article")) == len(ARTICLES_IDS)

    # check restore status
    restore_status = client.backup.get_restore_status(backup_id, BACKEND)
    assert restore_status.status == BackupStatus.SUCCESS


def test_fail_on_non_existing_class(client: weaviate.WeaviateClient) -> None:
    """Fail backup functions on non-existing class"""
    backup_id = _create_backup_id()
    class_name = "NonExistingClass"
    for func in [client.backup.create, client.backup.restore]:
        with pytest.raises(UnexpectedStatusCodeException) as excinfo:
            func(backup_id=backup_id, backend=BACKEND, include_collections=class_name)
            assert class_name in str(excinfo.value)
            assert "422" in str(excinfo.value)


def test_fail_restoring_backup_for_existing_class(client: weaviate.WeaviateClient) -> None:
    """Fail restoring backup for existing class."""
    backup_id = _create_backup_id()
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


def test_fail_creating_existing_backup(client: weaviate.WeaviateClient) -> None:
    """Fail creating existing backup."""
    backup_id = _create_backup_id()
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


def test_fail_restoring_non_existing_backup(client: weaviate.WeaviateClient) -> None:
    """Fail restoring non-existing backup."""
    backup_id = _create_backup_id()
    with pytest.raises(UnexpectedStatusCodeException) as excinfo:
        client.backup.restore(backup_id=backup_id, backend=BACKEND, wait_for_completion=True)
        assert backup_id in str(excinfo.value)
        assert "404" in str(excinfo.value)


def test_fail_checking_status_for_non_existing_restore(client: weaviate.WeaviateClient) -> None:
    """Fail checking restore status for non-existing restore."""
    backup_id = _create_backup_id()
    for func in [client.backup.get_restore_status, client.backup.get_create_status]:
        with pytest.raises(UnexpectedStatusCodeException) as excinfo:
            func(
                backup_id=backup_id,
                backend=BACKEND,
            )
            assert backup_id in str(excinfo)
            assert "404" in str(excinfo)


def test_fail_creating_backup_for_both_include_and_exclude_classes(
    client: weaviate.WeaviateClient,
) -> None:
    """Fail creating backup for both include and exclude classes."""
    backup_id = _create_backup_id()

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


def test_backup_and_restore_with_collection(client: weaviate.WeaviateClient) -> None:
    backup_id = _create_backup_id()

    article = client.collections.get("Article")

    # create backup
    create = article.backup.create(backup_id=backup_id, backend=BACKEND, wait_for_completion=True)
    assert create.status == BackupStatus.SUCCESS

    assert len(article) == len(ARTICLES_IDS)

    # check create status
    create_status = article.backup.get_create_status(backup_id, BACKEND)
    assert create_status.status == BackupStatus.SUCCESS

    # remove existing class
    client.collections.delete("Article")

    # restore backup
    restore = article.backup.restore(backup_id=backup_id, backend=BACKEND, wait_for_completion=True)
    assert restore.status == BackupStatus.SUCCESS

    # # check data exists again
    assert len(article) == len(ARTICLES_IDS)

    # check restore status
    restore_status = article.backup.get_restore_status(backup_id, BACKEND)
    assert restore_status.status == BackupStatus.SUCCESS
