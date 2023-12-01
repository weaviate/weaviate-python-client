import datetime
import time
from typing import Dict, Any, List

import pytest

import weaviate
from weaviate.exceptions import UnexpectedStatusCodeException, BackupFailedException

BACKUP_FILESYSTEM_PATH = "/tmp/backups"  # must be the same location as in the docker-compose file
BACKEND = "filesystem"

schema = {
    "classes": [
        {
            "class": "Paragraph",
            "properties": [
                {"dataType": ["text"], "name": "contents"},
                {"dataType": ["Paragraph"], "name": "hasParagraphs"},
            ],
        },
        {
            "class": "Article",
            "properties": [
                {"dataType": ["string"], "name": "title"},
                {"dataType": ["Paragraph"], "name": "hasParagraphs"},
                {"dataType": ["date"], "name": "datePublished"},
            ],
        },
    ]
}

paragraphs = [
    {"id": "fd34ccf4-1a2a-47ad-8446-231839366c3f", "properties": {"contents": "paragraph 1"}},
    {"id": "2653442b-05d8-4fa3-b46a-d4a152eb63bc", "properties": {"contents": "paragraph 2"}},
    {"id": "55374edb-17de-487f-86cb-9a9fbc30823f", "properties": {"contents": "paragraph 3"}},
    {"id": "124ff6aa-597f-44d0-8c13-62fbb1e66888", "properties": {"contents": "paragraph 4"}},
    {"id": "f787386e-7d1c-481f-b8c3-3dbfd8bbad85", "properties": {"contents": "paragraph 5"}},
]

articles = [
    {
        "id": "2fd68cbc-21ff-4e19-aaef-62531dade974",
        "properties": {
            "title": "article a",
            "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    },
    {
        "id": "7ea3f7b8-65fd-4318-a842-ae9ba38ffdca",
        "properties": {
            "title": "article b",
            "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    },
    {
        "id": "769a4280-4b85-4e67-b685-07796c49a764",
        "properties": {
            "title": "article c",
            "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    },
    {
        "id": "97fcc234-fd16-4a40-82bb-d614e9bddf8b",
        "properties": {
            "title": "article d",
            "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    },
    {
        "id": "3fa435d3-6ab2-489d-abed-c25ec526c9f4",
        "properties": {
            "title": "article e",
            "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    },
]


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    client.schema.create(schema)
    for para in paragraphs:
        client.data_object.create(para["properties"], "Paragraph", para["id"])
    for i, art in enumerate(articles):
        client.data_object.create(art["properties"], "Article", art["id"])
        client.data_object.reference.add(
            from_uuid=art["id"],
            from_class_name="Article",
            from_property_name="hasParagraphs",
            to_uuid=paragraphs[i]["id"],
            to_class_name="Paragraph",
        )
    yield client
    client.schema.delete_all()


def _assert_objects_exist(local_client: weaviate.Client, class_name: str, expected_count: int):
    result = local_client.query.aggregate(class_name).with_meta_count().do()
    count = result["data"]["Aggregate"][class_name][0]["meta"]["count"]
    assert (
        expected_count == count
    ), f"{class_name}: expected count: {expected_count}, received: {count}"


def _create_backup_id() -> str:
    return str(round(time.time() * 1000))


def _check_response(
    response: Dict[str, Any], backup_id: str, status: List[str], classes_include: List[str] = None
) -> None:
    assert response["id"] == backup_id
    if classes_include is not None:
        assert len(response["classes"]) == len(classes_include)
        assert sorted(response["classes"]) == sorted(classes_include)
    assert response["backend"] == "filesystem"
    assert response["path"] == f"{BACKUP_FILESYSTEM_PATH}/{backup_id}"
    assert response["status"] in status


def test_create_and_restore_backup_with_waiting(client, tmp_path) -> None:
    """Create and restore backup with waiting."""
    backup_id = _create_backup_id()
    # check data exists
    _assert_objects_exist(client, "Article", len(articles))
    _assert_objects_exist(client, "Paragraph", len(paragraphs))

    # create backup
    classes = ["Article", "Paragraph"]
    resp = client.backup.create(backup_id=backup_id, backend=BACKEND, wait_for_completion=True)
    _check_response(resp, backup_id, ["SUCCESS"], classes)

    # check data still exists
    _assert_objects_exist(client, "Article", len(articles))
    _assert_objects_exist(client, "Paragraph", len(paragraphs))

    # check create status
    resp = client.backup.get_create_status(backup_id, BACKEND)
    _check_response(resp, backup_id, ["SUCCESS"])

    # remove existing class
    client.schema.delete_class("Article")
    client.schema.delete_class("Paragraph")
    # restore backup
    resp = client.backup.restore(backup_id=backup_id, backend=BACKEND, wait_for_completion=True)
    _check_response(resp, backup_id, ["SUCCESS"], classes)

    # check data exists again
    _assert_objects_exist(client, "Article", len(articles))
    _assert_objects_exist(client, "Paragraph", len(paragraphs))
    # check restore status
    resp = client.backup.get_restore_status(backup_id, BACKEND)
    _check_response(resp, backup_id, ["SUCCESS"])


def test_create_and_restore_backup_without_waiting(client: weaviate.Client) -> None:
    """Create and restore backup without waiting."""
    backup_id = _create_backup_id()

    # check data exists
    _assert_objects_exist(client, "Article", len(articles))
    # create backup
    include = ["Article"]

    resp = client.backup.create(backup_id=backup_id, include_classes=include, backend=BACKEND)
    _check_response(resp, backup_id, ["STARTED"], include)

    # wait until created
    while True:
        resp = client.backup.get_create_status(backup_id, BACKEND)
        _check_response(resp, backup_id, ["STARTED", "TRANSFERRING", "TRANSFERRED", "SUCCESS"])
        if resp["status"] == "SUCCESS":
            break
        time.sleep(0.1)
    # check data still exists
    _assert_objects_exist(client, "Article", len(articles))
    # remove existing class
    client.schema.delete_class("Article")
    # restore backup
    resp = client.backup.restore(
        backup_id=backup_id,
        include_classes=include,
        backend=BACKEND,
    )
    _check_response(resp, backup_id, ["STARTED"], include)
    # wait until restored
    while True:
        resp = client.backup.get_restore_status(backup_id, BACKEND)
        _check_response(resp, backup_id, ["STARTED", "TRANSFERRING", "TRANSFERRED", "SUCCESS"])
        if resp["status"] == "SUCCESS":
            break
        time.sleep(0.1)
    # check data exists again
    _assert_objects_exist(client, "Article", len(articles))


def test_create_and_restore_1_of_2_classes(client: weaviate.Client) -> None:
    """Create and restore 1 of 2 classes."""
    backup_id = _create_backup_id()

    # check data exists
    _assert_objects_exist(client, "Article", len(articles))

    # create backup
    include = ["Article"]
    resp = client.backup.create(
        backup_id=backup_id, include_classes=include, backend=BACKEND, wait_for_completion=True
    )
    _check_response(resp, backup_id, ["SUCCESS"], include)

    # check data still exists
    _assert_objects_exist(client, "Article", len(articles))
    # check create status
    resp = client.backup.get_create_status(backup_id, BACKEND)
    _check_response(resp, backup_id, ["SUCCESS"])

    # remove existing class
    client.schema.delete_class("Article")
    # restore backup
    resp = client.backup.restore(
        backup_id=backup_id, include_classes=include, backend=BACKEND, wait_for_completion=True
    )
    _check_response(resp, backup_id, ["SUCCESS"], include)

    # check data exists again
    _assert_objects_exist(client, "Article", len(articles))
    # check restore status
    resp = client.backup.get_restore_status(backup_id, BACKEND)
    _check_response(resp, backup_id, ["SUCCESS"])


def test_fail_on_non_existing_backend(client: weaviate.Client) -> None:
    """Fail backup functions on non-existing backend"""
    backup_id = _create_backup_id()
    backend = "non-existing-backend"
    for func in [client.backup.create, client.backup.get_create_status, client.backup.restore]:
        with pytest.raises(ValueError) as excinfo:
            func(backup_id=backup_id, backend=backend)
            assert backend in str(excinfo.value)


def test_fail_on_non_existing_class(client: weaviate.Client) -> None:
    """Fail backup functions on non-existing class"""
    backup_id = _create_backup_id()
    class_name = "NonExistingClass"
    for func in [client.backup.create, client.backup.restore]:
        with pytest.raises(UnexpectedStatusCodeException) as excinfo:
            func(backup_id=backup_id, backend=BACKEND, include_classes=class_name)
            assert class_name in str(excinfo.value)
            assert "422" in str(excinfo.value)


def test_fail_restoring_backup_for_existing_class(client: weaviate.Client):
    """Fail restoring backup for existing class."""
    backup_id = _create_backup_id()
    class_name = ["Article"]
    resp = client.backup.create(
        backup_id=backup_id, include_classes=class_name, backend=BACKEND, wait_for_completion=True
    )
    _check_response(resp, backup_id, ["SUCCESS"], class_name)

    # fail restore
    with pytest.raises(BackupFailedException) as excinfo:
        client.backup.restore(
            backup_id=backup_id,
            include_classes=class_name,
            backend=BACKEND,
            wait_for_completion=True,
        )
        assert class_name[0] in str(excinfo.value)
        assert "already exists" in str(excinfo.value)


def test_fail_creating_existing_backup(client: weaviate.Client):
    """Fail creating existing backup"""
    backup_id = _create_backup_id()
    class_name = ["Article"]
    resp = client.backup.create(
        backup_id=backup_id, include_classes=class_name, backend=BACKEND, wait_for_completion=True
    )
    _check_response(resp, backup_id, ["SUCCESS"], class_name)

    # fail create
    with pytest.raises(UnexpectedStatusCodeException) as excinfo:
        client.backup.create(
            backup_id=backup_id,
            include_classes=class_name,
            backend=BACKEND,
            wait_for_completion=True,
        )
        assert backup_id in str(excinfo.value)
        assert "422" in str(excinfo.value)


def test_fail_restoring_non_existing_backup(client: weaviate.Client):
    """fail restoring non-existing backup"""
    backup_id = _create_backup_id()
    with pytest.raises(UnexpectedStatusCodeException) as excinfo:
        client.backup.restore(backup_id=backup_id, backend=BACKEND, wait_for_completion=True)
        assert backup_id in str(excinfo.value)
        assert "404" in str(excinfo.value)


def test_fail_checking_status_for_non_existing_restore(client: weaviate.Client):
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


def test_fail_creating_backup_for_both_include_and_exclude_classes(client: weaviate.Client):
    """fail creating backup for both include and exclude classes"""
    backup_id = _create_backup_id()

    for func in [client.backup.create, client.backup.restore]:
        with pytest.raises(TypeError) as excinfo:
            include = "Article"
            exclude = "Paragraph"
            func(
                backup_id=backup_id,
                include_classes=include,
                exclude_classes=exclude,
                backend=BACKEND,
                wait_for_completion=True,
            )
            assert "Either 'include_classes' OR 'exclude_classes' can be set, not both" in str(
                excinfo.value
            )
