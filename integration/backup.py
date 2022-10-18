import datetime
import time
import weaviate

from integration.integration_util import testmethod, TestFailedException
from weaviate.exceptions import UnexpectedStatusCodeException, BackupFailedException


schema = {
    "classes": [
        {
            "class": "Paragraph",
            "properties": [
                {
                    "dataType": ["text"],
                    "name": "contents"
                },
                {
                    "dataType": ["Paragraph"],
                    "name": "hasParagraphs"
                }
            ]
        },
        {
            "class": "Article",
            "properties": [
                {
                    "dataType": ["string"],
                    "name": "title"
                },
                {
                    "dataType": ["Paragraph"],
                    "name": "hasParagraphs"
                },
                {
                    "dataType": ["date"],
                    "name": "datePublished"
                }
            ]
        }
    ]
}

paragraphs = [
    {
        "id": "fd34ccf4-1a2a-47ad-8446-231839366c3f",
        "properties": {
            "contents": "paragraph 1"
        }
    },
    {
        "id": "2653442b-05d8-4fa3-b46a-d4a152eb63bc",
        "properties": {
            "contents": "paragraph 2"
        }
    },
    {
        "id": "55374edb-17de-487f-86cb-9a9fbc30823f",
        "properties": {
            "contents": "paragraph 3"
        }
    },
    {
        "id": "124ff6aa-597f-44d0-8c13-62fbb1e66888",
        "properties": {
            "contents": "paragraph 4"
        }
    },
    {
        "id": "f787386e-7d1c-481f-b8c3-3dbfd8bbad85",
        "properties": {
            "contents": "paragraph 5"
        }
    }
]

articles = [
    {
        "id": "2fd68cbc-21ff-4e19-aaef-62531dade974",
        "properties": {
            "title": "article a",
            "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    },
    {
        "id": "7ea3f7b8-65fd-4318-a842-ae9ba38ffdca",
        "properties": {
            "title": "article b",
            "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    },
    {
        "id": "769a4280-4b85-4e67-b685-07796c49a764",
        "properties": {
            "title": "article c",
            "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    },
    {
        "id": "97fcc234-fd16-4a40-82bb-d614e9bddf8b",
        "properties": {
            "title": "article d",
            "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    },
    {
        "id": "3fa435d3-6ab2-489d-abed-c25ec526c9f4",
        "properties": {
            "title": "article e",
            "datePublished": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    }
]

def make_backup_id():
    return str(round(time.time() * 1000))

class TestBackups:
    def __init__(self, client: weaviate.Client):
        client.schema.delete_all()
        self.client = client
        self.backup_dir = "/tmp/backups"

    def test(self):
        try:
            self._create_and_restore_backup_with_waiting()
            self._create_and_restore_backup_without_waiting()
            self._create_and_restore_1_of_2_classes()
            self._fail_creating_backup_on_non_existing_backend()
            self._fail_checking_create_status_on_non_existing_backend()
            self._fail_restoring_backup_on_non_existing_backend()
            self._fail_creating_backup_for_non_existing_class()
            self._fail_restoring_backup_for_existing_class()
            self._fail_creating_existing_backup()
            self._fail_checking_create_status_for_non_existing_backup()
            self._fail_restoring_non_existing_backup()
            self._fail_checking_restore_status_for_non_existing_restore()
            self._fail_creating_backup_for_both_include_and_exclude_classes()
            self._fail_restoring_backup_for_both_include_and_exclude_classes()
            self._log("done!")
        except:
            self._cleanup()
            raise TestFailedException("TestBackups failed")

    @testmethod
    def _create_and_restore_backup_with_waiting(self):
        self._log("create and restore backup with waiting")
        # check data exists
        self._assert_objects_exist("Article", len(articles))
        self._assert_objects_exist("Paragraph", len(paragraphs))
        # create backup
        backup_id = make_backup_id()
        backend = "filesystem"
        classes = ["Article", "Paragraph"]
        resp = self.client.backup.create(
            backup_id=backup_id,
            backend=backend,
            wait_for_completion=True
        )
        assert resp["id"] == backup_id
        assert sorted(resp["classes"]) == sorted(classes)
        assert resp["backend"] == backend
        assert resp["path"] == f"{self.backup_dir}/{backup_id}"
        assert resp["status"] == "SUCCESS"
        # check data still exists
        self._assert_objects_exist("Article", len(articles))
        self._assert_objects_exist("Paragraph", len(paragraphs))
        # check create status
        resp = self.client.backup.get_create_status(backup_id, backend)
        assert resp["id"] == backup_id
        assert resp["backend"] == backend
        assert resp["path"] == f"{self.backup_dir}/{backup_id}"
        assert resp["status"] == "SUCCESS"
        # remove existing class
        self.client.schema.delete_class("Article")
        self.client.schema.delete_class("Paragraph")
        # restore backup
        resp = self.client.backup.restore(
            backup_id=backup_id,
            backend=backend,
            wait_for_completion=True
        )
        assert resp["id"] == backup_id
        assert sorted(resp["classes"]) == sorted(classes)
        assert resp["backend"] == backend
        assert resp["path"] == f"{self.backup_dir}/{backup_id}"
        assert resp["status"] == "SUCCESS"
        # check data exists again
        self._assert_objects_exist("Article", len(articles))
        self._assert_objects_exist("Paragraph", len(paragraphs))
        # check restore status
        resp = self.client.backup.get_restore_status(backup_id, backend)
        assert resp["id"] == backup_id
        assert resp["backend"] == backend
        assert resp["path"] == f"{self.backup_dir}/{backup_id}"
        assert resp["status"] == "SUCCESS"

    @testmethod
    def _create_and_restore_backup_without_waiting(self):
        self._log("create and restore backup without waiting")
        # check data exists
        self._assert_objects_exist("Article", len(articles))
        # create backup
        backup_id = make_backup_id()
        backend = "filesystem"
        include = ["Article"]
        resp = self.client.backup.create(
            backup_id=backup_id,
            include_classes=include,
            backend=backend
        )
        assert resp["id"] == backup_id
        assert len(resp["classes"]) == 1
        assert resp["classes"] == include
        assert resp["backend"] == backend
        assert resp["path"] == f"{self.backup_dir}/{backup_id}"
        assert resp["status"] == "STARTED"
        # wait until created
        while True:
            resp = self.client.backup.get_create_status(backup_id, backend)
            assert resp["id"] == backup_id
            assert resp["backend"] == backend
            assert resp["path"] == f"{self.backup_dir}/{backup_id}"
            assert resp["status"] == "STARTED" or "TRANSFERRING" or "TRANSFERRED" or "SUCCESS"
            if resp["status"] == "SUCCESS":
                break
            time.sleep(0.1)
        # check data still exists
        self._assert_objects_exist("Article", len(articles))
        # remove existing class
        self.client.schema.delete_class("Article")
        # restore backup
        resp = self.client.backup.restore(
            backup_id=backup_id,
            include_classes=include,
            backend=backend,
        )
        assert resp["id"] == backup_id
        assert len(resp["classes"]) == 1
        assert resp["classes"] == include
        assert resp["backend"] == backend
        assert resp["path"] == f"{self.backup_dir}/{backup_id}"
        assert resp["status"] == "STARTED"
        # wait until restored
        while True:
            resp = self.client.backup.get_restore_status(backup_id, backend)
            assert resp["id"] == backup_id
            assert resp["backend"] == backend
            assert resp["path"] == f"{self.backup_dir}/{backup_id}"
            assert resp["status"] == "STARTED" or "TRANSFERRING" or "TRANSFERRED" or "SUCCESS"
            if resp["status"] == "SUCCESS":
                break
            time.sleep(0.1)
        # check data exists again
        self._assert_objects_exist("Article", len(articles))

    @testmethod
    def _create_and_restore_1_of_2_classes(self):
        self._log("create and restore 1 of 2 classes")
        # check data exists
        self._assert_objects_exist("Article", len(articles))
        # create backup
        backup_id = make_backup_id()
        backend = "filesystem"
        include = ["Article"]
        resp = self.client.backup.create(
            backup_id=backup_id,
            include_classes=include,
            backend=backend,
            wait_for_completion=True
        )
        assert resp["id"] == backup_id
        assert len(resp["classes"]) == 1
        assert resp["classes"] == include
        assert resp["backend"] == backend
        assert resp["path"] == f"{self.backup_dir}/{backup_id}"
        assert resp["status"] == "SUCCESS"
        # check data still exists
        self._assert_objects_exist("Article", len(articles))
        # check create status
        resp = self.client.backup.get_create_status(backup_id, backend)
        assert resp["id"] == backup_id
        assert resp["backend"] == backend
        assert resp["path"] == f"{self.backup_dir}/{backup_id}"
        assert resp["status"] == "SUCCESS"
        # remove existing class
        self.client.schema.delete_class("Article")
        # restore backup
        resp = self.client.backup.restore(
            backup_id=backup_id,
            include_classes=include,
            backend=backend,
            wait_for_completion=True
        )
        assert resp["id"] == backup_id
        assert len(resp["classes"]) == 1
        assert resp["classes"] == include
        assert resp["backend"] == backend
        assert resp["path"] == f"{self.backup_dir}/{backup_id}"
        assert resp["status"] == "SUCCESS"
        # check data exists again
        self._assert_objects_exist("Article", len(articles))
        # check restore status
        resp = self.client.backup.get_restore_status(backup_id, backend)
        assert resp["id"] == backup_id
        assert resp["backend"] == backend
        assert resp["path"] == f"{self.backup_dir}/{backup_id}"
        assert resp["status"] == "SUCCESS"
    
    @testmethod
    def _fail_creating_backup_on_non_existing_backend(self):
        self._log("fail creating backup on non-existing backend")
        backup_id = make_backup_id()
        backend = "non-existing-backend"
        try:
            self.client.backup.create(
                backup_id=backup_id,
                backend=backend,
            )
            raise TestFailedException("should have failed")
        except ValueError as e:
            assert backend in str(e)

    @testmethod
    def _fail_checking_create_status_on_non_existing_backend(self):
        self._log("fail checking create status on non-existing backend")
        backup_id = make_backup_id()
        backend = "non-existing-backend"
        try:
            self.client.backup.get_create_status(
                backup_id=backup_id,
                backend=backend,
            )
            raise TestFailedException("should have failed")
        except ValueError as e:
            assert backend in str(e)

    @testmethod
    def _fail_restoring_backup_on_non_existing_backend(self):
        self._log("fail restoring backup on non-existing backend")
        backup_id = make_backup_id()
        backend = "non-existing-backend"
        try:
            self.client.backup.restore(
                backup_id=backup_id,
                backend=backend,
            )
            raise TestFailedException("should have failed")
        except ValueError as e:
            assert backend in str(e)

    @testmethod
    def _fail_creating_backup_for_non_existing_class(self):
        self._log("fail creating backup for non-existing class")
        backup_id = make_backup_id()
        backend = "filesystem"
        class_name = "NonExistingClass"
        try:
            self.client.backup.create(
                backup_id=backup_id,
                backend=backend,
                include_classes=class_name
            )
            raise TestFailedException("should have failed")
        except UnexpectedStatusCodeException as e:
            assert class_name in str(e)
            assert "422" in str(e)

    @testmethod
    def _fail_restoring_backup_for_existing_class(self):
        self._log("fail restoring backup for existing class")
        # create backup
        backup_id = make_backup_id()
        backend = "filesystem"
        class_name = "Article"
        resp = self.client.backup.create(
            backup_id=backup_id,
            include_classes=class_name,
            backend=backend,
            wait_for_completion=True
        )
        assert resp["id"] == backup_id
        assert len(resp["classes"]) == 1
        assert resp["classes"] == [class_name]
        assert resp["backend"] == backend
        assert resp["path"] == f"{self.backup_dir}/{backup_id}"
        assert resp["status"] == "SUCCESS"
        # fail restore
        try:
            self.client.backup.restore(
                backup_id=backup_id,
                include_classes=class_name,
                backend=backend,
                wait_for_completion=True
            )
            raise TestFailedException("should have failed")
        except BackupFailedException as e:
            assert class_name in str(e)
            assert "already exists" in str(e)
    
    @testmethod
    def _fail_creating_existing_backup(self):
        self._log("fail creating existing backup")
        # create backup
        backup_id = make_backup_id()
        backend = "filesystem"
        class_name = "Article"
        resp = self.client.backup.create(
            backup_id=backup_id,
            include_classes=class_name,
            backend=backend,
            wait_for_completion=True
        )
        # fail create
        try:
            self.client.backup.create(
                backup_id=backup_id,
                include_classes=class_name,
                backend=backend,
                wait_for_completion=True
            )
        except UnexpectedStatusCodeException as e:
            assert backup_id in str(e)
            assert "422" in str(e)

    @testmethod
    def _fail_checking_create_status_for_non_existing_backup(self):
        self._log("fail checking create status for non-existing backup")
        backup_id = make_backup_id()
        backend = "filesystem"
        try:
            self.client.backup.get_create_status(
                backup_id=backup_id,
                backend=backend,
            )
            raise TestFailedException("should have failed")
        except UnexpectedStatusCodeException as e:
            assert backup_id in str(e)
            assert "404" in str(e)

    @testmethod
    def _fail_restoring_non_existing_backup(self):
        self._log("fail restoring non-existing backup")
        # fail restore
        backup_id = make_backup_id()
        backend = "filesystem"
        try:
            self.client.backup.restore(
                backup_id=backup_id,
                backend=backend,
                wait_for_completion=True
            )
        except UnexpectedStatusCodeException as e:
            assert backup_id in str(e)
            assert "404" in str(e)

    @testmethod
    def _fail_checking_restore_status_for_non_existing_restore(self):
        self._log("fail checking restore status for non-existing restore")
        # create backup
        backup_id = make_backup_id()
        backend = "filesystem"
        class_name = "Article"
        resp = self.client.backup.create(
            backup_id=backup_id,
            include_classes=class_name,
            backend=backend,
            wait_for_completion=True
        )
        # fail restore status
        try:
            self.client.backup.get_restore_status(
                backup_id=backup_id,
                backend=backend,
            )
        except UnexpectedStatusCodeException as e:
            assert backup_id in str(e)
            assert "404" in str(e)

    @testmethod
    def _fail_creating_backup_for_both_include_and_exclude_classes(self):
        self._log("fail creating backup for both include and exclude classes")
        try:
            backup_id = make_backup_id()
            backend = "filesystem"
            include = "Article"
            exclude = "Paragraph"
            resp = self.client.backup.create(
                backup_id=backup_id,
                include_classes=include,
                exclude_classes=exclude,
                backend=backend,
                wait_for_completion=True
            )
            return TestFailedException("should have failed")
        except TypeError as e:
            assert "Either 'include_classes' OR 'exclude_classes' can be set, not both" in str(e)

    @testmethod
    def _fail_restoring_backup_for_both_include_and_exclude_classes(self):
        self._log("fail restoring backup for both include and exclude classes")
        try:
            backup_id = make_backup_id()
            backend = "filesystem"
            include = "Article"
            exclude = "Paragraph"
            resp = self.client.backup.restore(
                backup_id=backup_id,
                include_classes=include,
                exclude_classes=exclude,
                backend=backend,
                wait_for_completion=True
            )
            return TestFailedException("should have failed")
        except TypeError as e:
            assert "Either 'include_classes' OR 'exclude_classes' can be set, not both" in str(e)

    def _setup(self):
        self.client.schema.create(schema)
        self._createParagraphs()
        self._createArticles()
        time.sleep(2.0)

    def _createParagraphs(self):
        for _, para in enumerate(paragraphs):
            self.client.data_object.create(para["properties"], "Paragraph", para["id"])

    def _createArticles(self):
        for i, art in enumerate(articles):
            self.client.data_object.create(art["properties"], "Article", art["id"])
            self.client.data_object.reference.add(
                from_uuid=art["id"],
                from_class_name="Article",
                from_property_name="hasParagraphs",
                to_uuid=paragraphs[i]["id"],
                to_class_name="Paragraph"
            )

    def _cleanup(self):
        for _, cls in enumerate(schema["classes"]):
            self.client.schema.delete_class(cls["class"])


    def _assert_objects_exist(self, class_name, expected_count):
        result = self.client.query \
            .aggregate(class_name) \
            .with_meta_count() \
            .do()
        count = result["data"]["Aggregate"][class_name][0]["meta"]["count"]
        if expected_count == count:
            return
        raise Exception(f"{class_name}: expected count: {expected_count}, received: {count}")

    def _log(self, msg):
        print(f"TestBackups: {msg}")


if __name__ == "__main__":
    client = weaviate.Client("http://localhost:8080")
    bu = TestBackups(client)
    bu.test()
