from http.server import HTTPServer

import pytest as pytest

import weaviate
from mock_tests.conftest import MOCK_SERVER_URL


@pytest.mark.parametrize(
    "version,warning", [("1.16.0", True), ("1.17.2", True), ("1.17.3", False), ("1.18.0", False)]
)
def test_warning_old_weaviate(recwarn, ready_mock: HTTPServer, version: str, warning: bool):
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": version})
    client = weaviate.Client(MOCK_SERVER_URL)

    client.query.get("Class", ["Property"]).with_generate(single_prompt="something")

    if warning:
        assert any(str(w.message).startswith("Dep003") for w in recwarn)
    else:
        assert not any(str(w.message).startswith("Dep003") for w in recwarn)
