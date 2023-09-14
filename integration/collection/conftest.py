import os
from typing import Any, Dict, List

import pytest
import requests

from weaviate.collection import Collection
from weaviate.config import Config
from weaviate.connect import Connection


def _collection(rest: int, grpc: int, headers: Dict[str, str]):
    config = Config(grpc_port_experimental=grpc)
    connection = Connection(
        url=f"http://localhost:{rest}",
        auth_client_secret=None,
        timeout_config=(10, 60),
        proxies=None,
        trust_env=False,
        additional_headers=headers,
        startup_period=5,
        connection_config=config.connection_config,
        embedded_db=None,
        grcp_port=config.grpc_port_experimental,
    )
    return Collection(connection)


def _clear(rest: int) -> None:
    res = requests.get(f"http://localhost:{rest}/v1/schema")
    if res.status_code == 200:
        schema = res.json()
        for class_ in schema["classes"]:
            res = requests.delete(f"http://localhost:{rest}/v1/schema/{class_['class']}")
            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(f"Failed to delete the test data of {class_}: {res.text}")
    else:
        raise Exception(f"Failed retrieve the full schema: {res.text}")


@pytest.fixture(scope="module")
def collection_basic():
    try:
        yield _collection(8080, 50051, {})
    finally:
        _clear(8080)


@pytest.fixture(scope="module")
def collection_multinode():
    try:
        yield _collection(8087, 50058, {})
    finally:
        _clear(8087)


@pytest.fixture(scope="module")
def collection_openai():
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")
    try:
        yield _collection(
            8086, 50057, {"X-OpenAI-Api-Key": api_key}
        )  # ports with generative module
    finally:
        _clear(8086)


@pytest.fixture(scope="module")
def collection_openai_invalid_key():
    try:
        yield _collection(8086, 50057, {"X-OpenAI-Api-Key": "IamNotValid"})
    finally:
        _clear(8086)


@pytest.fixture(scope="module")
def collection_openai_no_module():
    try:
        yield _collection(
            8080, 50051, {"X-OpenAI-Api-Key": "doesnt matter"}
        )  # main version that does not have a generative module
    finally:
        _clear(8080)


def ids_from_data(data: List[Any]) -> List[int]:
    return list(range(len(data)))
