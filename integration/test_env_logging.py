import os
import logging
import pytest
from typing import Generator

import weaviate
from integration.conftest import ClientFactory, AsyncClientFactory

class LogCaptureHandler(logging.Handler):
    """Handler to capture log messages for testing."""
    def __init__(self):
        super().__init__()
        self.logs: list[str] = []
        
    def emit(self, record):
        self.logs.append(record.getMessage())

@pytest.fixture
def log_capture() -> Generator[LogCaptureHandler, None, None]:
    """Fixture to capture logs from the weaviate-client logger."""
    handler = LogCaptureHandler()
    logger = logging.getLogger("weaviate-client")
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)

@pytest.fixture
def mock_client(monkeypatch):
    """Fixture to create a client with mocked HTTP responses."""
    from unittest.mock import AsyncMock, MagicMock
    from httpx import Response, Request
    
    async def mock_get(*args, **kwargs):
        if "/.well-known/ready" in str(args[0]):
            return Response(200, request=Request("GET", args[0]))
        elif "/.well-known/live" in str(args[0]):
            return Response(200, request=Request("GET", args[0]))
        elif "/v1/meta" in str(args[0]):
            return Response(200, json={"version": "1.28.2"}, request=Request("GET", args[0]))
        return Response(404, request=Request("GET", args[0]))

    async def mock_post(*args, **kwargs):
        return Response(200, json={"status": "success"}, request=Request("POST", args[0]))

    client = weaviate.WeaviateClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        skip_init_checks=True,
    )
    
    # Mock the HTTP methods
    client._connection._client = MagicMock()
    client._connection._client.get = AsyncMock(side_effect=mock_get)
    client._connection._client.post = AsyncMock(side_effect=mock_post)
    
    return client

def test_default_logging_behavior(mock_client, log_capture: LogCaptureHandler) -> None:
    """Test that logging is disabled by default (INFO level)."""
    assert mock_client.is_ready()  # This will make an HTTP request
    
    # No debug logs should be present at INFO level
    assert not any("Request:" in log for log in log_capture.logs)
    assert not any("Response:" in log for log in log_capture.logs)

def test_debug_logging_enabled(mock_client, log_capture: LogCaptureHandler) -> None:
    """Test that debug logging is enabled when WEAVIATE_LOG_LEVEL=DEBUG."""
    # Enable debug logging
    os.environ["WEAVIATE_LOG_LEVEL"] = "DEBUG"
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(logging.DEBUG)
    
    mock_client.get_meta()  # Make a request that will be logged
    
    # Verify logs contain request and response info
    assert any("Request:" in log for log in log_capture.logs)
    assert any("Response:" in log for log in log_capture.logs)
    assert any("Headers:" in log for log in log_capture.logs)
    
    # Verify sensitive headers are masked
    auth_logs = [log for log in log_capture.logs if "authorization" in log.lower()]
    for log in auth_logs:
        assert "[...]" in log
    
    cookie_logs = [log for log in log_capture.logs if "cookie" in log.lower()]
    for log in cookie_logs:
        assert "=..." in log

@pytest.mark.asyncio
async def test_debug_logging_async(mock_client, log_capture: LogCaptureHandler) -> None:
    """Test that debug logging works with async client."""
    # Enable debug logging
    os.environ["WEAVIATE_LOG_LEVEL"] = "DEBUG"
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(logging.DEBUG)
    
    await mock_client.get_meta()  # Make a request that will be logged
    
    # Verify logs contain request and response info
    assert any("Request:" in log for log in log_capture.logs)
    assert any("Response:" in log for log in log_capture.logs)
    assert any("Headers:" in log for log in log_capture.logs)

def test_debug_logging_with_collection_operations(
    mock_client,
    log_capture: LogCaptureHandler,
    request: pytest.FixtureRequest,
    monkeypatch
) -> None:
    """Test that debug logging captures collection operations."""
    from unittest.mock import AsyncMock, MagicMock
    import grpc
    from weaviate.proto.v1 import weaviate_pb2, weaviate_pb2_grpc
    
    name = request.node.name
    
    # Mock gRPC stub and channel
    mock_stub = MagicMock()
    mock_channel = MagicMock()
    
    # Mock gRPC responses
    mock_search_response = weaviate_pb2.SearchReply()
    mock_stub.Search = AsyncMock(return_value=mock_search_response)
    
    # Set up gRPC mocks
    mock_client._connection._grpc_stub = mock_stub
    mock_client._connection._grpc_channel = mock_channel
    
    # Enable debug logging
    os.environ["WEAVIATE_LOG_LEVEL"] = "DEBUG"
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(logging.DEBUG)
    
    try:
        # Create collection
        collection = mock_client.collections.create(
            name=name,
            vectorizer_config=weaviate.collections.classes.config.Configure.Vectorizer.none(),
            properties=[
                weaviate.collections.classes.config.Property(
                    name="name",
                    data_type=weaviate.collections.classes.config.DataType.TEXT
                ),
            ],
        )
        
        # Add data
        collection.data.insert({"name": "test"})
        
        # Query data
        collection.query.fetch_objects()
        
        # Verify HTTP logs
        create_logs = [log for log in log_capture.logs if 'Request: POST' in log and '/v1/schema' in log]
        assert len(create_logs) > 0, "Collection creation request not logged"
        
        insert_logs = [log for log in log_capture.logs if 'Request: POST' in log and '/objects' in log]
        assert len(insert_logs) > 0, "Data insertion not logged"
        
        # Verify gRPC logs
        query_logs = [log for log in log_capture.logs if 'Method: Search' in log]
        assert len(query_logs) > 0, "Query operation not logged"
        
        # Verify request details are logged
        assert any(name in log for log in log_capture.logs), f"Collection name '{name}' not found in logs"
    
    finally:
        mock_client.collections.delete(name)
