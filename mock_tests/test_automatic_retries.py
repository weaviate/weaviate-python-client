import json
from typing import Optional

import pytest
import uuid
from werkzeug.wrappers import Request, Response

import weaviate
from mock_tests.conftest import MOCK_SERVER_URL
from weaviate.batch.crud_batch import WeaviateErrorRetryConf, BatchResponse
from weaviate.util import check_batch_result


@pytest.mark.parametrize(
    "error",
    [
        {"errors": {"error": [{"message": "I'm an error message"}]}},
        {
            "errors": {
                "error": [{"message": "I'm an error message"}, {"message": "Another message"}]
            }
        },
    ],
)
def test_automatic_retry_obs(weaviate_mock, error):
    """Tests that all objects are successfully added even if half of them fail."""
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
                obj["result"] = error
                num_failed_requests += 1
        return Response(json.dumps(objects))

    weaviate_mock.expect_request("/v1/batch/objects").respond_with_handler(handler)

    client = weaviate.Client(MOCK_SERVER_URL)
    added_uuids = []
    batch_size = 4  # Do not change, affects how many failed requests there are
    n = (
        50 * batch_size
    )  # multiple of the batch size, otherwise it is difficult to calculate the number of expected errors
    client.batch.configure(
        batch_size=batch_size,
        num_workers=2,
        weaviate_error_retries=WeaviateErrorRetryConf(number_retries=3),
        dynamic=False,
    )

    with client.batch as batch:
        for i in range(n):
            added_uuids.append(uuid.uuid4())
            batch.add_data_object({"name": "test" + str(i)}, "test", added_uuids[-1])
    assert len(successfully_added) == n
    assert sorted(successfully_added) == sorted(added_uuids)

    # with a batch size of 4, we have 3 failures per batch
    assert num_failed_requests == 3 * n / batch_size


def test_automatic_retry_refs(weaviate_mock):
    """Tests that all references are successfully added even if half of them fail."""
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

    client = weaviate.Client(MOCK_SERVER_URL)
    batch_size = 4  # Do not change, affects how many failed requests there are
    n = (
        50 * batch_size
    )  # multiple of the batch size, otherwise it is difficult to calculate the number of expected errors
    with client.batch(
        batch_size=batch_size,
        weaviate_error_retries=WeaviateErrorRetryConf(number_retries=3),
        num_workers=2,
        dynamic=False,
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
    """Test automatic retry that cannot add all objects."""
    num_success_requests = 0

    # Mockserver returns error for half of all objects
    def handler(request: Request):
        nonlocal num_success_requests
        objects = request.json["objects"]
        for j, obj in enumerate(objects):
            obj["deprecations"] = None
            if j % 2 == 0:
                obj["result"] = {}
                num_success_requests += 1
            else:
                obj["result"] = {"errors": {"error": [{"message": "I'm an error message"}]}}
        return Response(json.dumps(objects))

    weaviate_mock.expect_request("/v1/batch/objects").respond_with_handler(handler)

    client = weaviate.Client(MOCK_SERVER_URL)
    batch_size = 20
    n = batch_size * 2
    with client.batch(
        batch_size=batch_size,
        weaviate_error_retries=WeaviateErrorRetryConf(number_retries=1),
        num_workers=2,
        callback=None,
    ) as batch:
        for i in range(n):
            batch.add_data_object({"name": "test" + str(i)}, "test", uuid.uuid4())
        batch.flush()
    # retried 3 times, starting with 200 objects and half off all objects succeed each time
    assert num_success_requests == 30


@pytest.mark.parametrize(
    "retry_config",
    [None, WeaviateErrorRetryConf(number_retries=1), WeaviateErrorRetryConf(number_retries=2)],
)
def test_print_threadsafety(weaviate_mock, capfd, retry_config):
    """Test retry with callback and callback threadsafety."""
    num_success_requests = 0

    # Mockserver returns error for half of all objects
    def handler(request: Request):
        nonlocal num_success_requests
        objects = request.json["objects"]
        for j, obj in enumerate(objects):
            obj["deprecations"] = None
            if j % 2 == 0:
                obj["result"] = {}
                num_success_requests += 1
            else:
                obj["result"] = {"errors": {"error": [{"message": "I'm an error message"}]}}
        return Response(json.dumps(objects))

    weaviate_mock.expect_request("/v1/batch/objects").respond_with_handler(handler)

    client = weaviate.Client(MOCK_SERVER_URL)

    added_uuids = []
    n = 200 * 4
    with client.batch(
        batch_size=200,
        callback=check_batch_result,
        num_workers=4,
        weaviate_error_retries=retry_config,
    ) as batch:
        for i in range(n):
            added_uuids.append(uuid.uuid4())
            batch.add_data_object({"name": "test" + str(i)}, "test", added_uuids[-1])

    retry_factor: float = 1.0
    if retry_config is not None:
        retry_factor = 1 / (2 * retry_config.number_retries)
    assert num_success_requests == n - n / 2 * retry_factor

    # half of all objects fail => N/2 print statements that end with a newline
    print_output, err = capfd.readouterr()
    assert print_output.count("\n") == n - num_success_requests


@pytest.mark.parametrize(
    "retry_config, expected",
    [
        (WeaviateErrorRetryConf(number_retries=1, errors_to_include=["include", "maybe"]), 300),
        (WeaviateErrorRetryConf(number_retries=1, errors_to_exclude=["reject", "maybe"]), 250),
    ],
)
def test_include_error(weaviate_mock, retry_config, expected):
    """Test that objects are included/excluded based on their error message"""
    num_success_requests = 0

    # Mockserver returns error for 3/4 of all objects, with different messages for each quarter
    def handler(request: Request):
        nonlocal num_success_requests
        objects = request.json["objects"]
        for j, obj in enumerate(objects):
            obj["deprecations"] = None
            if j % 4 == 0:
                obj["result"] = {}
                num_success_requests += 1
            elif j % 4 == 1:
                obj["result"] = {"errors": {"error": [{"message": "include me"}]}}
            elif j % 4 == 2:
                obj["result"] = {"errors": {"error": [{"message": "maybe retry maybe not"}]}}
            else:
                obj["result"] = {
                    "errors": {"error": [{"message": "reject me"}, {"message": "other error"}]}
                }
        return Response(json.dumps(objects))

    weaviate_mock.expect_request("/v1/batch/objects").respond_with_handler(handler)

    client = weaviate.Client(MOCK_SERVER_URL)

    added_uuids = []
    n = 400 * 2
    with client.batch(
        batch_size=400,
        callback=None,
        num_workers=2,
        weaviate_error_retries=retry_config,
    ) as batch:
        for i in range(n):
            added_uuids.append(uuid.uuid4())
            batch.add_data_object({"name": "test" + str(i)}, "test", added_uuids[-1])

    assert num_success_requests == expected


def test_callback_for_successful_responses(weaviate_mock, capfd):
    """Test that all objects reach teh callback, even when a part of a batch is retried."""

    # have some objects fail
    def handler(request: Request):
        objects = request.json["objects"]
        for j, obj in enumerate(objects):
            obj["deprecations"] = None
            if j % 2 == 0:
                obj["result"] = {}
            else:
                obj["result"] = {"errors": {"error": [{"message": "I'm an error message"}]}}
        return Response(json.dumps(objects))

    weaviate_mock.expect_request("/v1/batch/objects").respond_with_handler(handler)

    client = weaviate.Client(MOCK_SERVER_URL)

    def callback_print_all(results: Optional[BatchResponse]):
        if results is None:
            return
        for _ in results:
            print("I saw that object")

    added_uuids = []
    n = 200 * 4
    with client.batch(
        batch_size=200,
        callback=callback_print_all,
        num_workers=4,
        weaviate_error_retries=WeaviateErrorRetryConf(number_retries=1),
    ) as batch:
        for i in range(n):
            added_uuids.append(uuid.uuid4())
            batch.add_data_object({"name": "test" + str(i)}, "test", added_uuids[-1])

    # callback output for each object
    print_output, err = capfd.readouterr()
    assert print_output.count("\n") == n
