import json
import re
import time

import pytest
import uuid
from requests import ReadTimeout
from werkzeug.wrappers import Request, Response

import weaviate
from mock_tests.conftest import MOCK_SERVER_URL


def test_no_retry_on_timeout(weaviate_no_auth_mock):
    """Tests that expected timeout exception is raised."""

    def handler(request: Request):
        time.sleep(1.5)  # cause timeout
        return Response(json.dumps({}))

    weaviate_no_auth_mock.expect_request("/v1/batch/objects").respond_with_handler(handler)

    client = weaviate.Client(MOCK_SERVER_URL, timeout_config=(1, 1))

    n = 10
    with pytest.raises(ReadTimeout):
        with client.batch(batch_size=n, timeout_retries=0, dynamic=False) as batch:
            for _ in range(n):
                batch.add_data_object({"name": "test"}, "test", uuid.uuid4())


def test_retry_on_timeout(weaviate_no_auth_mock):
    """Tests that clients resends objects that haven't been added due to a timeout.

    After the timeout, the client checks if
    - An object with the given UUID already exists (using HEAD). Here 50% return that they do NOT exist, eg have to be
    resent.
    - If an object exists, it is checked if the current version in weaviate is identical to the one that is
    sent in the batch. If not, the object in the batch is an update and has to be resent again

    In total 75% are resend.
    """
    added_uuids = []
    first_request = True
    n = 20  # needs to be divisible by 4

    def handler_batch_objects(request: Request):
        nonlocal first_request, n
        if first_request:
            assert len(request.json["objects"]) == n  # all objects are send the first time
            time.sleep(1)  # cause timeout
            first_request = False
        else:
            # 75% of objects have to be resent
            assert len(request.json["objects"]) == n / 4 * 3

        return Response(json.dumps([]))

    weaviate_no_auth_mock.expect_request("/v1/batch/objects").respond_with_handler(
        handler_batch_objects
    )

    # 50% of objects have not been added
    def handler_exists(request: Request):
        if added_uuids.index(request.url.split("/")[-1]) % 2 == 0:
            return Response(json.dumps({}), status=404)
        else:
            return Response(json.dumps({}), status=200)

    weaviate_no_auth_mock.expect_request(
        re.compile("^/v1/objects/Test/"), method="HEAD"
    ).respond_with_handler(handler_exists)

    # 50% of objects are an update to an existing objects and have to be resent
    flip = False

    def handler_get_object(request: Request):
        nonlocal flip
        val = "test" if flip else "other"
        flip = not flip
        return Response(json.dumps({"properties": {"name": val}}))

    weaviate_no_auth_mock.expect_request(
        re.compile("^/v1/objects/Test/"), method="GET"
    ).respond_with_handler(handler_get_object)

    client = weaviate.Client(MOCK_SERVER_URL, timeout_config=(1, 1))
    with client.batch(batch_size=n, timeout_retries=1, dynamic=False) as batch:
        for _ in range(n):
            added_uuids.append(str(uuid.uuid4()))
            batch.add_data_object({"name": "test"}, "test", added_uuids[-1])
    weaviate_no_auth_mock.check_assertions()


def test_retry_on_timeout_all_succesfull(weaviate_no_auth_mock):
    """Test that the client does not resend an empty batch."""
    n = 20

    # handler only responds once => error if a batch is resent
    def handler_batch_objects(request: Request):
        nonlocal n
        assert len(request.json["objects"]) == n  # all objects are send the first time
        time.sleep(1)  # cause timeout
        return Response(json.dumps([]))

    weaviate_no_auth_mock.expect_oneshot_request("/v1/batch/objects").respond_with_handler(
        handler_batch_objects
    )

    # return that all objects are already added successful
    weaviate_no_auth_mock.expect_request(
        re.compile("^/v1/objects/Test/"), method="HEAD"
    ).respond_with_response(Response(json.dumps({}), status=200))
    weaviate_no_auth_mock.expect_request(
        re.compile("^/v1/objects/Test/"), method="GET"
    ).respond_with_json({"properties": {"name": "test"}})

    client = weaviate.Client(MOCK_SERVER_URL, timeout_config=(1, 1))
    with client.batch(batch_size=n, timeout_retries=1, dynamic=False) as batch:
        for _ in range(n):
            batch.add_data_object({"name": "test"}, "test", uuid.uuid4())
    weaviate_no_auth_mock.check_assertions()
