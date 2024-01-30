from datetime import datetime

import pytest
from pytest_httpserver import HTTPServer

import weaviate
from mock_tests.conftest import MOCK_SERVER_URL, MOCK_PORT, MOCK_IP

from weaviate.exceptions import UnexpectedStatusCodeError, WeaviateStartUpError


@pytest.mark.skip(reason="Fails with gRPC not enabled error")
def test_warning_old_weaviate(recwarn: pytest.WarningsRecorder, ready_mock: HTTPServer) -> None:
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": "1.21.0"})
    ready_mock.expect_request("/v1/objects").respond_with_json({})

    client = weaviate.WeaviateClient(MOCK_SERVER_URL)
    client.collections.get("Class").data.insert(
        {
            "date": datetime.now(),
        }
    )

    assert len(recwarn) == 1
    w = recwarn.pop()
    assert issubclass(w.category, UserWarning)
    assert str(w.message).startswith("Con002")


def test_status_code_exception(weaviate_mock: HTTPServer) -> None:
    weaviate_mock.expect_request("/v1/schema/Test").respond_with_json(response_json={}, status=403)

    client = weaviate.connect_to_local(port=MOCK_PORT, host=MOCK_IP, skip_init_checks=True)
    collection = client.collections.get("Test")
    with pytest.raises(UnexpectedStatusCodeError) as e:
        collection.config.get()
    assert e.value.status_code == 403
    weaviate_mock.check_assertions()


def test_old_version(ready_mock: HTTPServer) -> None:
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": "1.23.4"})
    with pytest.raises(WeaviateStartUpError):
        weaviate.connect_to_local(port=MOCK_PORT, host=MOCK_IP, skip_init_checks=True)
    ready_mock.check_assertions()
