import json
import uuid

import pytest
from werkzeug.wrappers import Request, Response

import weaviate
from weaviate.batch.crud_batch import CallbackMode
from weaviate.exceptions import BatchImportFailedException
from weaviate.util import check_batch_result


def test_automatic_retry_obs(weaviate_mock):
    """Tests that all objects are successfully added even if half of them fail"""
    successfully_added = []
    num_failed_requests = 0

    # Mockserver returns error for half of all objects
    def handler(request: Request):
        nonlocal num_failed_requests
        objects = request.json["objects"]
        for j, obj in enumerate(objects):
            obj["deprecations"] = None
            if j % 2 == 0:
                obj["result"] = {}
                successfully_added.append(uuid.UUID(obj["id"]))
            else:
                obj["result"] = {"errors": {"error": [{"message": "I'm an error message"}]}}
                num_failed_requests += 1
        return Response(json.dumps(objects))

    weaviate_mock.expect_request("/v1/batch/objects").respond_with_handler(handler)

    client = weaviate.Client(url="http://127.0.0.1:23534")
    added_uuids = []
    batch_size = 4  # Do not change, affects how many failed requests there are
    n = (
        50 * batch_size
    )  # multiple of the batch size, otherwise it is difficult to calculate the number of expected errors
    with client.batch(
        batch_size=batch_size,
        callback=CallbackMode.RETRY_FAILED,
        num_workers=2,
        weaviate_error_retries=3,
    ) as batch:
        for i in range(n):
            added_uuids.append(uuid.uuid4())
            batch.add_data_object({"name": "test" + str(i)}, "test", added_uuids[-1])
    assert len(successfully_added) == n
    assert sorted(successfully_added) == sorted(added_uuids)

    # with a batch size of 4, we have 3 failures per batch
    assert num_failed_requests == 3 * n / batch_size


def test_automatic_retry_refs(weaviate_mock):
    """Tests that all objects are successfully added even if half of them fail"""
    num_success_requests = 0
    num_failed_requests = 0

    # Mockserver returns error for half of all objects
    def handler(request: Request):
        nonlocal num_failed_requests, num_success_requests
        objects = request.json
        for j, obj in enumerate(objects):
            obj["deprecations"] = None
            if j % 2 == 0:
                obj["result"] = {}
                num_success_requests += 1
            else:
                obj["result"] = {"errors": {"error": [{"message": "I'm an error message"}]}}
                num_failed_requests += 1
        return Response(json.dumps(objects))

    weaviate_mock.expect_request("/v1/batch/references").respond_with_handler(handler)

    client = weaviate.Client(url="http://127.0.0.1:23534")
    batch_size = 4  # Do not change, affects how many failed requests there are
    n = (
        50 * batch_size
    )  # multiple of the batch size, otherwise it is difficult to calculate the number of expected errors
    with client.batch(
        batch_size=batch_size, callback=CallbackMode.RETRY_FAILED, num_workers=2
    ) as batch:
        for _ in range(n):
            batch.add_reference(
                from_property_name="Property",
                from_object_class_name="SomeClass",
                from_object_uuid=str(uuid.uuid4()),
                to_object_class_name="otherClass",
                to_object_uuid=str(uuid.uuid4()),
            )
    assert num_success_requests == n

    # with a batch size of 4, we have 3 failures per batch
    assert num_failed_requests == 3 * n / batch_size


def test_automatic_retry_unsuccessful(weaviate_mock):
    """Test that exception is raised when retry is unsuccessful."""

    def handler(request: Request):
        objects = request.json["objects"]
        for _, obj in enumerate(objects):
            obj["deprecations"] = None
            obj["result"] = {"errors": {"error": [{"message": "I'm an error message"}]}}
        return Response(json.dumps(objects))

    weaviate_mock.expect_request("/v1/batch/objects").respond_with_handler(handler)

    client = weaviate.Client(url="http://127.0.0.1:23534")
    n = 50 * 4
    batch_size = 2
    with pytest.raises(BatchImportFailedException):
        with client.batch(
            batch_size=batch_size, callback=CallbackMode.RETRY_FAILED, num_workers=2
        ) as batch:
            for i in range(n):
                batch.add_data_object({"name": "test" + str(i)}, "test", uuid.uuid4())


@pytest.mark.parametrize("callback", [CallbackMode.REPORT_ERRORS, None, check_batch_result])
def test_print_threadsafety(weaviate_mock, capfd, callback):
    """Test that the default callback calling print statements is threadsafe."""
    successfully_added = []

    # Mockserver returns error for half of all objects
    def handler(request: Request):
        objects = request.json["objects"]
        for j, obj in enumerate(objects):
            obj["deprecations"] = None
            if j % 2 == 0:
                obj["result"] = {}
                successfully_added.append(obj["id"])
            else:
                obj["result"] = {"errors": {"error": [{"message": "I'm an error message"}]}}
        return Response(json.dumps(objects))

    weaviate_mock.expect_request("/v1/batch/objects").respond_with_handler(handler)

    client = weaviate.Client(url="http://127.0.0.1:23534")

    added_uuids = []
    n = 50 * 4
    with client.batch(batch_size=4, callback=callback, num_workers=4) as batch:
        for i in range(n):
            added_uuids.append(uuid.uuid4())
            batch.add_data_object({"name": "test" + str(i)}, "test", added_uuids[-1])
    assert len(successfully_added) == n / 2

    # half of all objects fail => N/2 print statements that end with a newline
    print_output, err = capfd.readouterr()
    if callback is not None:
        assert print_output.count("\n") == n / 2
