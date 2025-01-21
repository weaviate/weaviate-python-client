import json
import logging
import textwrap
from typing import Generator, Optional

import pytest
from _pytest.fixtures import SubRequest

import weaviate
from integration.conftest import ClientFactory, AsyncClientFactory
from weaviate.collections import Collection
from weaviate.collections.classes.config import Configure, Property, DataType
from weaviate.config import AdditionalConfig

class CustomLogger:
    """Custom logger class to capture logs for testing."""
    def __init__(self):
        self.logs = []

    def debug(self, msg: str) -> None:
        self.logs.append(msg)

    def info(self, msg: str) -> None:
        self.logs.append(msg)

@pytest.fixture
def custom_logger() -> Generator[CustomLogger, None, None]:
    logger = CustomLogger()
    yield logger

def test_default_logger_behavior(client_factory: ClientFactory) -> None:
    """Test that the default logger is used when no custom logger is provided."""
    client = client_factory()
    assert client.is_ready()  # This will make an HTTP request
    # Default logger should not log HTTP requests by default
    # This test verifies backwards compatibility

def test_custom_logger_sync(client_factory: ClientFactory, custom_logger: CustomLogger) -> None:
    """Test that a custom logger receives HTTP request/response logs."""
    # Create client with custom logger
    client = weaviate.WeaviateClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        additional_config=AdditionalConfig(logger=custom_logger),
        skip_init_checks=False,
    )
    client.connect()

    # Make a request that will be logged
    client.get_meta()

    # Verify logs contain request and response info
    assert any("Request:" in log for log in custom_logger.logs)
    assert any("Response:" in log for log in custom_logger.logs)
    assert any("Headers:" in log for log in custom_logger.logs)

    # Verify sensitive headers are masked
    auth_logs = [log for log in custom_logger.logs if "authorization" in log.lower()]
    for log in auth_logs:
        assert "[...]" in log

    cookie_logs = [log for log in custom_logger.logs if "cookie" in log.lower()]
    for log in cookie_logs:
        assert "=..." in log

@pytest.mark.asyncio
async def test_custom_logger_async(async_client_factory: AsyncClientFactory, custom_logger: CustomLogger) -> None:
    """Test that a custom logger works with async client."""
    # Create async client with custom logger
    client = weaviate.WeaviateAsyncClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        additional_config=AdditionalConfig(logger=custom_logger),
        skip_init_checks=False,
    )
    await client.connect()

    # Make a request that will be logged
    await client.get_meta()

    # Verify logs contain request and response info
    assert any("Request:" in log for log in custom_logger.logs)
    assert any("Response:" in log for log in custom_logger.logs)
    assert any("Headers:" in log for log in custom_logger.logs)

def test_standard_python_logger(client_factory: ClientFactory) -> None:
    """Test that a standard Python logger works."""
    # Set up a standard Python logger
    logger = logging.getLogger("test-weaviate-client")
    logger.setLevel(logging.DEBUG)
    log_capture = []
    
    class ListHandler(logging.Handler):
        def emit(self, record):
            log_capture.append(record.getMessage())
    
    logger.addHandler(ListHandler())

    # Create client with standard logger
    client = weaviate.WeaviateClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        additional_config=AdditionalConfig(logger=logger),
        skip_init_checks=False,
    )
    client.connect()

    # Make a request that will be logged
    client.get_meta()

    # Verify logs contain request and response info
    assert any("Request:" in log for log in log_capture)
    assert any("Response:" in log for log in log_capture)
    assert any("Headers:" in log for log in log_capture)

def test_logger_with_collection_operations(
    client_factory: ClientFactory,
    custom_logger: CustomLogger,
    request: SubRequest
) -> None:
    """Test that logger captures collection operations."""
    name = request.node.name
    
    # Create client with custom logger
    client = weaviate.WeaviateClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        additional_config=AdditionalConfig(logger=custom_logger),
        skip_init_checks=False,
    )
    client.connect()
    
    try:
        # Create collection
        collection = client.collections.create(
            name=name,
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="name", data_type=DataType.TEXT),
            ],
        )

        # Add data
        collection.data.insert({"name": "test"})

        # Query data
        results = collection.query.fetch_objects()

        # Verify logs for each operation
        create_logs = [log for log in custom_logger.logs if "POST" in log and name in log]
        assert len(create_logs) > 0, "Collection creation not logged"

        insert_logs = [log for log in custom_logger.logs if "POST" in log and "objects" in log]
        assert len(insert_logs) > 0, "Data insertion not logged"

        query_logs = [log for log in custom_logger.logs if "GET" in log and "objects" in log]
        assert len(query_logs) > 0, "Query operation not logged"

    finally:
        client.collections.delete(name)
