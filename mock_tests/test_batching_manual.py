import uuid

import weaviate
from mock_tests.conftest import MOCK_SERVER_URL


def test_manual_batching_warning_object(recwarn, weaviate_mock):
    weaviate_mock.expect_request("/v1/batch/objects").respond_with_json([])

    client = weaviate.Client(url=MOCK_SERVER_URL)

    client.batch.configure(batch_size=None, dynamic=False)
    client.batch.add_data_object({}, "ExistingClass")
    client.batch.create_objects()

    assert len(recwarn) == 1
    w = recwarn.pop()
    assert issubclass(w.category, DeprecationWarning)
    assert str(w.message).startswith("Dep002")


def test_manual_batching_warning_ref(recwarn, weaviate_mock):
    weaviate_mock.expect_request("/v1/batch/references").respond_with_json([])

    client = weaviate.Client(url=MOCK_SERVER_URL)

    client.batch.configure(batch_size=None, dynamic=False)
    client.batch.add_reference(
        str(uuid.uuid4()), "NonExistingClass", "existsWith", str(uuid.uuid4()), "OtherClass"
    )
    client.batch.create_references()

    assert len(recwarn) == 1
    w = recwarn.pop()
    assert issubclass(w.category, DeprecationWarning)
    assert str(w.message).startswith("Dep002")


def test_manual_batching_warning_object_when_default_dynamic_batching_enabled(
    recwarn, weaviate_mock
):
    weaviate_mock.expect_request("/v1/batch/objects").respond_with_json([])

    client = weaviate.Client(url=MOCK_SERVER_URL)

    client.batch.add_data_object({}, "ExistingClass")
    client.batch.create_objects()

    assert len(recwarn) == 1
    w = recwarn.pop()
    assert issubclass(w.category, DeprecationWarning)
    assert str(w.message).startswith("Dep003")


def test_manual_batching_warning_ref_when_default_dynamic_batching_enabled(recwarn, weaviate_mock):
    weaviate_mock.expect_request("/v1/batch/references").respond_with_json([])

    client = weaviate.Client(url=MOCK_SERVER_URL)

    client.batch.add_reference(
        str(uuid.uuid4()), "NonExistingClass", "existsWith", str(uuid.uuid4()), "OtherClass"
    )
    client.batch.create_references()

    assert len(recwarn) == 1
    w = recwarn.pop()
    assert issubclass(w.category, DeprecationWarning)
    assert str(w.message).startswith("Dep003")
