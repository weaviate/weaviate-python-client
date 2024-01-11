import pytest

import weaviate
from mock_tests.conftest import MOCK_SERVER_URL
from weaviate.exceptions import ResponseCannotBeDecodedException


def test_json_decode_exception_dict(weaviate_mock):
    """Tests that JsonDecodeException is raised containing the correct error."""

    weaviate_mock.expect_request("/v1/schema").respond_with_data("JsonCannotParseThis")

    client = weaviate.Client(MOCK_SERVER_URL)
    with pytest.raises(ResponseCannotBeDecodedException) as e:
        client.schema.get()

        assert "JsonCannotParseThis" in e.value


def test_json_decode_exception_list(weaviate_mock):
    """Tests that JsonDecodeException is raised containing the correct error."""

    weaviate_mock.expect_request("/v1/schema/Test/shards").respond_with_data("JsonCannotParseThis")

    client = weaviate.Client(MOCK_SERVER_URL)
    with pytest.raises(ResponseCannotBeDecodedException) as e:
        client.schema.get_class_shards("Test")
        assert "JsonCannotParseThis" in e.value
