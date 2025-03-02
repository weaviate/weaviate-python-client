import os
import sys
import json
import logging
import importlib
import pytest
import httpx
from typing import Generator

import weaviate
from integration.conftest import ClientFactory, AsyncClientFactory
from weaviate.collections.classes.config import Configure, Property, DataType


class LogCaptureHandler(logging.Handler):
    """Handler to capture log messages for testing."""

    def __init__(self):
        super().__init__()
        self.logs: list[str] = []
        self.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter("%(message)s")

    def emit(self, record):
        try:
            msg = self.format(record)
            if msg:
                # For multi-line messages, store each line
                lines = msg.split("\n")
                for line in lines:
                    # Store all lines, including empty ones for proper formatting
                    self.logs.append(line)
                    print(f"LogCaptureHandler captured: {line!r}", file=sys.stderr)
        except Exception as e:
            self.handleError(record)
            print(f"Error in LogCaptureHandler.emit: {e}", file=sys.stderr)

    def get_logs(self) -> list[str]:
        """Get all captured logs."""
        return self.logs

    def clear(self):
        """Clear captured logs."""
        self.logs = []

    def get_full_log(self) -> str:
        """Get all logs joined together."""
        return "\n".join(self.logs)


@pytest.fixture
def log_capture(monkeypatch) -> Generator[LogCaptureHandler, None, None]:
    """Fixture to capture logs from the weaviate-client logger."""
    # Store original configuration
    logger = logging.getLogger("weaviate-client")
    original_config = {
        "handlers": list(logger.handlers),
        "level": logger.level,
        "propagate": logger.propagate,
    }

    # Reset logging configuration
    logging.shutdown()
    logging.root.handlers = []

    # Create and configure handler
    handler = LogCaptureHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(message)s"))

    # Reset all logging configuration
    logging.shutdown()
    logging.root.handlers = []

    # Configure root logger to capture all logs
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)

    # Configure weaviate-client logger
    logger = logging.getLogger("weaviate-client")
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True  # Enable propagation for test capture

    # Set environment variable and reload logger module AFTER handlers are configured
    monkeypatch.setenv("WEAVIATE_LOG_LEVEL", "DEBUG")
    import importlib
    import weaviate.logger

    importlib.reload(weaviate.logger)  # This will use our already configured handlers

    # Ensure the logger is properly configured after reload
    logger = logging.getLogger("weaviate-client")
    if not any(isinstance(h, LogCaptureHandler) for h in logger.handlers):
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True

    yield handler

    # Restore original configuration
    logger = logging.getLogger("weaviate-client")
    logger.handlers = original_config["handlers"]
    logger.setLevel(original_config["level"])
    logger.propagate = original_config["propagate"]

    # Reset root logger
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.setLevel(logging.WARNING)

    # Clear captured logs
    handler.clear()

    # Reset environment variable
    monkeypatch.delenv("WEAVIATE_LOG_LEVEL", raising=False)


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

    from weaviate.util import _ServerVersion
    from httpx import Response, Request, AsyncClient

    client = weaviate.WeaviateClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        skip_init_checks=True,
    )

    from weaviate.collections import Collection
    from weaviate.collections.classes.config import Configure, Property, DataType

    # Create a proper mock AsyncClient that will trigger logging
    async def mock_send(request):
        """Mock send that triggers logging"""
        url = str(request.url)
        url = url.replace("/v1/v1/", "/v1/")  # Clean up URL (remove duplicate v1)

        # Process request content
        request_content = None
        if request.content:
            try:
                content = request.content.decode("utf-8")
                request_content = json.loads(content)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Add test headers with sensitive information
        request.headers.update(
            {
                "Authorization": "Bearer fake-test-token",
                "Cookie": "session=fake-test-session",
                "X-Api-Key": "fake-test-api-key",
                "Secret-Key": "fake-super-secret",
                "Token": "fake-user-token",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Api-Key",
                "host": "localhost:8080",
            }
        )

        # Determine response based on URL pattern
        status_code = 404
        json_data = None

        if "/.well-known/" in url:
            status_code = 200
        elif "/v1/meta" in url:
            status_code = 200
            json_data = {"version": "1.28.2"}
        elif "/v1/schema" in url and request_content:
            status_code = 200
            json_data = {
                "status": "success",
                "class": request_content.get("class", ""),
                "properties": request_content.get("properties", []),
                "vectorizer": request_content.get("vectorizer", "none"),
            }
        elif "/v1/objects" in url and request_content:
            status_code = 200
            json_data = {
                "id": "test-id",
                "class": request_content.get("class", "TestCollection"),
                "properties": request_content,
                "status": "success",
            }

        # Prepare response data
        response_data = json.dumps(json_data, indent=2) if json_data is not None else ""

        # Create response with sensitive headers
        response = Response(
            status_code=status_code,
            content=response_data.encode() if response_data else None,
            request=request,
            headers={
                "content-type": "application/json",
                "Set-Cookie": "session=test-response-session",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Api-Key",
                "content-length": str(len(response_data)) if response_data else "0",
                "x-request-id": "test-request-id",
                "x-correlation-id": "test-correlation-id",
                "server": "weaviate/1.28.2",
                "Authorization": "Bearer fake-test-token",
                "Secret-Key": "fake-super-secret",
                "Token": "fake-user-token",
                "X-Api-Key": "fake-test-api-key",
            },
        )

        # Import and use logger
        from weaviate.logger import log_http_event

        # Only log if the logger level is DEBUG
        logger = logging.getLogger("weaviate-client")
        if logger.getEffectiveLevel() <= logging.DEBUG:
            await log_http_event(response)

        return response

    # Create a proper mock AsyncClient that will trigger logging
    mock_client = AsyncMock(spec=AsyncClient)

    # Ensure build_request returns a proper Request object with headers and content
    def mock_build_request(method, url, **kwargs):
        headers = kwargs.get("headers", {})
        json_data = kwargs.get("json")
        content = kwargs.get("content")

        if "content-type" not in headers:
            headers["content-type"] = "application/json"

        if json_data is not None:
            content = json.dumps(json_data).encode("utf-8")
            headers["content-length"] = str(len(content))
        elif content is not None:
            headers["content-length"] = str(len(content))
        else:
            headers["content-length"] = "0"

        # Add test headers with sensitive information
        headers.update(
            {
                "Authorization": "Bearer fake-test-token",
                "Cookie": "session=fake-test-session",
                "X-Api-Key": "fake-test-api-key",
                "Secret-Key": "fake-super-secret",
                "Token": "fake-user-token",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Api-Key",
                "host": "localhost:8080",
            }
        )

        return Request(method, url, headers=headers, content=content)

    mock_client.build_request = MagicMock(side_effect=mock_build_request)
    mock_client.get = AsyncMock(side_effect=mock_send)
    mock_client.post = AsyncMock(side_effect=mock_send)
    mock_client.delete = AsyncMock(side_effect=mock_send)
    mock_client.put = AsyncMock(side_effect=mock_send)
    mock_client.head = AsyncMock(side_effect=mock_send)
    mock_client.patch = AsyncMock(side_effect=mock_send)
    mock_client.send = AsyncMock(side_effect=mock_send)

    # Set up mock client and stubs
    mock_stub = MagicMock()
    mock_stub.Search = AsyncMock(return_value=MagicMock(results=[]))

    # Configure client connection
    client._connection._client = mock_client
    client._connection._grpc_stub = mock_stub
    client._connection._grpc_channel = MagicMock()
    client._connection._weaviate_version = _ServerVersion.from_string("1.23.7")
    client._connection.__connected = True

    # Ensure the client's logger is properly configured
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    if not any(isinstance(h, LogCaptureHandler) for h in logger.handlers):
        handler = LogCaptureHandler()
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)

    # Mock client and collection operations
    client.connect = AsyncMock()

    # Create a proper mock for get_meta that triggers logging
    async def mock_get_meta():
        request = httpx.Request("GET", "http://localhost:8080/v1/meta")
        request.headers.update(
            {
                "Authorization": "Bearer fake-test-token",
                "Cookie": "session=fake-test-session",
                "X-Api-Key": "fake-test-api-key",
            }
        )
        response = httpx.Response(
            200,
            json={"version": "1.23.7"},
            request=request,
            headers={
                "content-type": "application/json",
                "Set-Cookie": "session=fake-test-response-session",
                "Authorization": "Bearer fake-test-token",
            },
        )
        # Import and use logger
        from weaviate.logger import log_http_event

        # Only log if the logger level is DEBUG
        logger = logging.getLogger("weaviate-client")
        if logger.getEffectiveLevel() <= logging.DEBUG:
            await log_http_event(response)
        return {"version": "1.23.7"}

    # Use AsyncMock with side_effect instead of direct assignment
    client.get_meta = AsyncMock(side_effect=mock_get_meta)
    client.is_ready = MagicMock(return_value=True)
    client._connection.is_connected = MagicMock(return_value=True)

    async def mock_create_collection(*args, **kwargs):
        name = kwargs.get("name", "test")
        # Create collection schema
        await client._connection.post(
            path="/v1/schema",
            weaviate_object={
                "class": name,
                "vectorizer": "none",
                "properties": [{"name": "name", "dataType": ["text"]}],
            },
        )

        # Create mock collection with operations
        mock_collection = MagicMock(spec=Collection)
        mock_collection._name = name
        mock_collection.data = MagicMock()

        # Mock insert operation to properly log object creation
        async def mock_insert(data):
            # Structure the object data properly
            object_data = {"class": name, "properties": data}
            # Get the logger and ensure it's properly configured
            logger = logging.getLogger("weaviate-client")
            logger.setLevel(logging.DEBUG)

            return await client._connection.post(path="/v1/objects", weaviate_object=object_data)

        mock_collection.data.insert = AsyncMock(side_effect=mock_insert)

        # Mock query operation to properly log gRPC calls
        async def mock_fetch_objects():
            # This will trigger gRPC logging via the mock stub
            from weaviate.proto.v1 import search_get_pb2

            request = search_get_pb2.SearchRequest(collection=name)

            # Get the logger and ensure it's properly configured
            logger = logging.getLogger("weaviate-client")
            logger.setLevel(logging.DEBUG)

            # Create a mock response
            mock_response = MagicMock()
            mock_response.results = []

            # Log the gRPC event with method name
            from weaviate.logger import log_grpc_event

            log_grpc_event("Search", request, mock_response)

            return mock_response.results

        mock_collection.query = MagicMock()
        mock_collection.query.fetch_objects = AsyncMock(side_effect=mock_fetch_objects)

        return mock_collection

    # Set up collections mock
    client.collections = MagicMock()
    client.collections.create = AsyncMock(side_effect=mock_create_collection)
    client.collections.delete = AsyncMock(
        side_effect=lambda name: client._connection.delete(path=f"/v1/schema/{name}")
    )

    return client


@pytest.mark.asyncio
async def test_default_logging_behavior(mock_client, log_capture: LogCaptureHandler) -> None:
    """Test that logging is disabled by default (INFO level)."""
    # Set log level to INFO explicitly
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(logging.INFO)
    os.environ["WEAVIATE_LOG_LEVEL"] = "INFO"

    await mock_client.connect()  # Connect the client first
    assert mock_client.is_ready()  # This will make an HTTP request

    # No debug logs should be present at INFO level
    assert not any("Request:" in log for log in log_capture.logs)
    assert not any("Response:" in log for log in log_capture.logs)


@pytest.mark.asyncio
async def test_debug_logging_enabled(
    mock_client, log_capture: LogCaptureHandler, monkeypatch
) -> None:
    """Test that debug logging is enabled when WEAVIATE_LOG_LEVEL=DEBUG."""
    # Enable debug logging and reload logger module
    monkeypatch.setenv("WEAVIATE_LOG_LEVEL", "DEBUG")
    import importlib
    import weaviate.logger

    importlib.reload(weaviate.logger)

    # Clear any existing logs
    log_capture.clear()

    # Configure root logger first
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(log_capture)
    root_logger.setLevel(logging.DEBUG)

    # Configure weaviate-client logger
    logger = logging.getLogger("weaviate-client")
    logger.handlers = []
    logger.addHandler(log_capture)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True  # Ensure propagation is enabled

    # Add various sensitive headers to test masking
    headers = {
        "Authorization": "Bearer secret-token",
        "Cookie": "session=12345",
        "X-Api-Key": "api-key-value",
        "X-Secret-Token": "secret-value",
        "Access-Token": "access-token-value",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Api-Key",
        "Set-Cookie": "session=67890; Path=/",
        "Api-Key": "another-api-key",
        "Secret-Key": "super-secret",
        "Token": "user-token",
    }
    mock_client._connection._headers.update(headers)

    # Make a request to trigger logging
    collection = await mock_client.collections.create(
        name="TestLogging",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
    )

    try:
        # Helper function to verify log presence
        def assert_log_contains(pattern: str, message: str):
            """Assert that a pattern exists in any log line, case-insensitive."""
            matching_logs = [log for log in log_capture.logs if pattern.lower() in log.lower()]
            assert len(matching_logs) > 0, f"{message}\nCaptured logs: {log_capture.logs}"

        # Verify basic logging sections
        assert_log_contains("Request: ", "No request logs found")
        assert_log_contains("Response: status_code=", "No response logs found")
        assert_log_contains("Headers:", "No headers logs found")

        # Verify header masking
        header_masks = {
            "authorization": "[...]",
            "cookie": "=...",
            "api-key": "[...]",
            "secret": "[...]",
            "token": "[...]",
            "access-control-allow-headers": "[...]",
            "set-cookie": "=...",
        }

        for header, mask in header_masks.items():
            logs = [log for log in log_capture.logs if header in log.lower()]
            assert len(logs) > 0, f"No logs found containing {header}"
            assert all(mask in log for log in logs), f"Header '{header}' not properly masked"

        # Insert data and query to test gRPC logging
        await collection.data.insert({"name": "test"})
        await collection.query.fetch_objects()

        # Verify gRPC logs
        assert_log_contains("Method: Search", "gRPC Search operation not logged")
        assert_log_contains("gRPC Request", "gRPC request section not logged")
        assert_log_contains("gRPC Response", "gRPC response section not logged")
        assert_log_contains("TestLogging", "Collection name not found in gRPC logs")

    finally:
        mock_client.collections.delete("TestLogging")


@pytest.mark.asyncio
async def test_debug_logging_async(
    mock_client, log_capture: LogCaptureHandler, monkeypatch
) -> None:
    """Test that debug logging works with async client and gRPC operations."""
    # Enable debug logging and reload logger module
    monkeypatch.setenv("WEAVIATE_LOG_LEVEL", "DEBUG")
    import importlib
    import weaviate.logger

    importlib.reload(weaviate.logger)

    # Configure root logger first
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(log_capture)
    root_logger.setLevel(logging.DEBUG)

    # Configure weaviate-client logger
    logger = logging.getLogger("weaviate-client")
    logger.handlers = []
    logger.addHandler(log_capture)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True  # Ensure propagation is enabled

    # Clear any existing logs AFTER configuring loggers
    log_capture.clear()

    # Create a proper mock for get_meta that triggers logging
    async def mock_get_meta():
        request = httpx.Request("GET", "http://localhost:8080/v1/meta")
        request.headers.update(
            {
                "Authorization": "Bearer fake-test-token",
                "Cookie": "session=fake-test-session",
                "X-Api-Key": "fake-test-api-key",
            }
        )
        response = httpx.Response(
            200,
            json={"version": "1.23.7"},
            request=request,
            headers={
                "content-type": "application/json",
                "Set-Cookie": "session=fake-test-response-session",
                "Authorization": "Bearer fake-test-token",
            },
        )
        # Import and use logger
        from weaviate.logger import log_http_event

        # Only log if the logger level is DEBUG
        logger = logging.getLogger("weaviate-client")
        if logger.getEffectiveLevel() <= logging.DEBUG:
            await log_http_event(response)
        return {"version": "1.23.7"}

    # Replace get_meta with our mock using AsyncMock with side_effect
    from unittest.mock import AsyncMock

    mock_client.get_meta = AsyncMock(side_effect=mock_get_meta)

    await mock_client.connect()

    # Test HTTP logging
    await mock_client.get_meta()
    assert any("Request: " in log for log in log_capture.logs), "No HTTP request logs found"
    assert any(
        "Response: status_code=" in log for log in log_capture.logs
    ), "No HTTP response logs found"
    assert any("Headers:" in log for log in log_capture.logs), "No HTTP header logs found"

    # Test gRPC logging with collection operations
    collection = await mock_client.collections.create(
        name="TestAsyncGrpcLogging",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
    )

    try:
        # Insert data and perform query to trigger gRPC logging
        await collection.data.insert({"name": "test"})
        await collection.query.fetch_objects()

        # Verify gRPC logging content
        assert any("gRPC Request" in log for log in log_capture.logs), "No gRPC request logs found"
        assert any(
            "gRPC Response" in log for log in log_capture.logs
        ), "No gRPC response logs found"
        assert any(
            "Method: Search" in log for log in log_capture.logs
        ), "gRPC method name not logged"
        assert any(
            "TestAsyncGrpcLogging" in log for log in log_capture.logs
        ), "Collection name not found in gRPC logs"

        # Verify any sensitive headers in gRPC metadata are masked
        metadata_logs = [log for log in log_capture.logs if "authorization" in log.lower()]
        for log in metadata_logs:
            assert "[...]" in log, "Authorization metadata not masked in gRPC logs"
    finally:
        await mock_client.collections.delete("TestAsyncGrpcLogging")


@pytest.mark.asyncio
async def test_concurrent_logging(mock_client, log_capture: LogCaptureHandler, monkeypatch) -> None:
    """Test that logging works correctly with concurrent requests."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    import grpc

    # Enable debug logging and reload logger module
    monkeypatch.setenv("WEAVIATE_LOG_LEVEL", "DEBUG")

    # Clear any existing logs and handlers
    log_capture.clear()
    logging.shutdown()

    # Configure root logger first
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(log_capture)
    root_logger.setLevel(logging.DEBUG)

    # Configure weaviate-client logger
    logger = logging.getLogger("weaviate-client")
    logger.handlers = []
    logger.addHandler(log_capture)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True  # Ensure propagation is enabled

    # Force reload logger module to pick up new environment variable
    import importlib
    import weaviate.logger

    importlib.reload(weaviate.logger)

    # Ensure the logger module's logger instance is properly configured
    weaviate.logger.logger.handlers = []
    weaviate.logger.logger.addHandler(log_capture)
    weaviate.logger.logger.setLevel(logging.DEBUG)
    weaviate.logger.logger.propagate = True

    # Helper function to verify log presence
    def assert_log_contains(pattern: str, message: str):
        matching_logs = [log for log in log_capture.logs if pattern in log]
        assert len(matching_logs) > 0, f"{message}\nCaptured logs: {log_capture.logs}"

    # Set up test collections
    collection_names = [f"TestConcurrent{i}" for i in range(3)]
    collections = []

    try:
        # Create collections and run operations concurrently
        async def create_and_operate(name: str):
            collection = await mock_client.collections.create(
                name=name,
                vectorizer_config=Configure.Vectorizer.none(),
                properties=[
                    Property(name="name", data_type=DataType.TEXT),
                ],
            )
            collections.append(collection)
            await collection.data.insert({"name": f"test_{name}"})
            await collection.query.fetch_objects()
            return collection

        # Run all operations concurrently
        await asyncio.gather(*[create_and_operate(name) for name in collection_names])

        # Verify basic logging for each collection
        for name in collection_names:
            # Verify schema creation logs
            assert_log_contains(f'"class": "{name}"', f"Schema creation not logged for {name}")
            assert_log_contains(
                f"POST http://localhost:8080/v1/v1/schema",
                f"Schema creation request not logged for {name}",
            )

            # Verify data insertion logs
            assert_log_contains(f"test_{name}", f"Data insertion not logged for {name}")
            assert_log_contains(
                f"POST http://localhost:8080/v1/v1/objects",
                f"Object creation request not logged for {name}",
            )

            # Verify gRPC query logs
            assert_log_contains(f'collection: "{name}"', f"gRPC query not logged for {name}")
            assert_log_contains("Method: Search", f"gRPC Search method not logged for {name}")

        # Verify sensitive header masking
        header_masks = {
            "authorization": "[...]",
            "cookie": "=...",
            "api-key": "[...]",
            "secret": "[...]",
            "token": "[...]",
            "access-control-allow-headers": "[...]",
            "set-cookie": "=...",
        }

        for header, mask in header_masks.items():
            logs = [log for log in log_capture.logs if header in log.lower()]
            assert len(logs) > 0, f"No logs found containing {header}"
            assert all(mask in log for log in logs), f"Header '{header}' not properly masked"

    finally:
        # Clean up collections
        for name in collection_names:
            await mock_client.collections.delete(name)


@pytest.mark.asyncio
async def test_invalid_log_level_behavior(
    mock_client, log_capture: LogCaptureHandler, monkeypatch
) -> None:
    """Test that invalid log levels default to INFO and disable debug logging."""

    # Helper function to verify log absence
    def assert_no_log_contains(patterns: list[str], message: str):
        assert not any(any(p in log for p in patterns) for log in log_capture.logs), message

    # Clear any existing logs
    log_capture.clear()

    # Set invalid log level and reload logger module
    monkeypatch.setenv("WEAVIATE_LOG_LEVEL", "INVALID")
    import importlib
    import weaviate.logger

    importlib.reload(weaviate.logger)

    # Configure weaviate-client logger to INFO level
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(logging.INFO)

    await mock_client.connect()
    await mock_client.get_meta()

    # Verify no debug logs are present
    assert_no_log_contains(["Request:", "Response:"], "Debug logs found with invalid log level")


@pytest.mark.asyncio
async def test_no_log_level_defaults_to_info(
    mock_client, log_capture: LogCaptureHandler, monkeypatch
) -> None:
    """Test that when WEAVIATE_LOG_LEVEL is not set, logging defaults to INFO."""

    # Helper function to verify log absence
    def assert_no_log_contains(patterns: list[str], message: str):
        assert not any(any(p in log for p in patterns) for log in log_capture.logs), message

    # Clear any existing logs
    log_capture.clear()

    # Remove log level environment variable and reload logger module
    monkeypatch.delenv("WEAVIATE_LOG_LEVEL", raising=False)
    import importlib
    import weaviate.logger

    importlib.reload(weaviate.logger)

    # Configure weaviate-client logger to INFO level (default)
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(logging.INFO)

    await mock_client.connect()
    await mock_client.get_meta()

    # Verify no debug logs are present
    assert_no_log_contains(["Request:", "Response:"], "Debug logs found when log level not set")


@pytest.mark.asyncio
async def test_info_level_disables_debug_logging(
    mock_client, log_capture: LogCaptureHandler, monkeypatch
) -> None:
    """Test that setting WEAVIATE_LOG_LEVEL to INFO disables debug logging."""

    # Helper function to verify log absence
    def assert_no_log_contains(patterns: list[str], message: str):
        assert not any(any(p in log for p in patterns) for log in log_capture.logs), message

    # Clear any existing logs
    log_capture.clear()

    # Set log level to INFO and reload logger module
    monkeypatch.setenv("WEAVIATE_LOG_LEVEL", "INFO")
    import importlib
    import weaviate.logger

    importlib.reload(weaviate.logger)

    # Configure weaviate-client logger to INFO level
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(logging.INFO)

    await mock_client.connect()
    await mock_client.get_meta()

    # Verify no debug logs are present
    assert_no_log_contains(["Request:", "Response:"], "Debug logs found when level set to INFO")
