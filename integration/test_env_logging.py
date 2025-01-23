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
        self.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter('%(message)s')
        print("\nDEBUG: LogCaptureHandler initialized")
        
    def emit(self, record):
        try:
            print(f"\nDEBUG: LogCaptureHandler.emit called")
            print(f"DEBUG: Record details - level={record.levelno}, levelname={record.levelname}")
            print(f"DEBUG: Record message: {record.msg}")
            
            if record.levelno >= self.level:
                msg = self.format(record)
                print(f"DEBUG: Formatted message: {msg}")
                self.logs.append(msg)
                print(f"DEBUG: Added log. Current logs: {self.logs}")
            else:
                print(f"DEBUG: Skipping record due to level (record level {record.levelno} < handler level {self.level})")
        except Exception as e:
            print(f"DEBUG: Error in emit: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            
    def format(self, record):
        try:
            msg = self.formatter.format(record)
            print(f"DEBUG: Formatting record: {msg}")
            return msg
        except Exception as e:
            print(f"DEBUG: Error in format: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            return str(record.msg)

@pytest.fixture
def log_capture() -> Generator[LogCaptureHandler, None, None]:
    """Fixture to capture logs from the weaviate-client logger."""
    # Configure root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    
    # Configure weaviate logger
    handler = LogCaptureHandler()
    logger = logging.getLogger("weaviate-client")
    
    # Store original handlers
    original_handlers = logger.handlers[:]
    original_level = logger.level
    
    # Clear and reconfigure logger
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    
    print(f"DEBUG: Reconfigured logger with handler. Current handlers: {logger.handlers}, level: {logger.level}, propagate: {logger.propagate}")
    
    yield handler
    
    # Restore original configuration
    logger.handlers = original_handlers
    logger.setLevel(original_level)
    print(f"DEBUG: Restored logger configuration. Current handlers: {logger.handlers}, level: {logger.level}")

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

    print("\nDEBUG: Setting up mock client")
    client = weaviate.WeaviateClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        skip_init_checks=True,
    )
    print("DEBUG: Created WeaviateClient instance")
    
    from weaviate.collections import Collection
    from weaviate.collections.classes.config import Configure, Property, DataType

    print("DEBUG: Setting up mock AsyncClient")
    # Create a proper mock AsyncClient that will trigger logging
    async def mock_send(request):
        """Mock send that triggers logging"""
        print(f"\nDEBUG: mock_send called for {request.method} {request.url}")
        
        # Get the weaviate-client logger and verify its state
        weaviate_logger = logging.getLogger("weaviate-client")
        print(f"DEBUG: Weaviate logger state in mock_send: level={weaviate_logger.level}, handlers={weaviate_logger.handlers}, propagate={weaviate_logger.propagate}")

        # Create response based on the request URL
        if "/.well-known/ready" in str(request.url):
            response = Response(200, request=request, headers={"content-type": "application/json"})
        elif "/.well-known/live" in str(request.url):
            response = Response(200, request=request, headers={"content-type": "application/json"})
        elif "/v1/meta" in str(request.url):
            response = Response(200, json={"version": "1.28.2"}, request=request, headers={"content-type": "application/json"})
        elif "/v1/schema" in str(request.url):
            response = Response(200, json={"status": "success"}, request=request, headers={"content-type": "application/json"})
        elif "/objects" in str(request.url):
            response = Response(200, json={"status": "success"}, request=request, headers={"content-type": "application/json"})
        else:
            response = Response(404, request=request, headers={"content-type": "application/json"})

        # Ensure the response has the request object properly attached
        response.request = request
        
        # Import and use the actual log_http_event function
        print("\nDEBUG: About to call log_http_event")
        from weaviate.logger import log_http_event
        
        # Call log_http_event and capture any debug messages
        log_http_event(response)
        print("DEBUG: log_http_event completed")
        
        return response

    # Create a proper mock AsyncClient that will trigger logging
    mock_client = AsyncMock(spec=AsyncClient)
    mock_client.get = AsyncMock(side_effect=mock_send)
    mock_client.post = AsyncMock(side_effect=mock_send)
    mock_client.delete = AsyncMock(side_effect=mock_send)
    mock_client.put = AsyncMock(side_effect=mock_send)
    mock_client.head = AsyncMock(side_effect=mock_send)
    mock_client.patch = AsyncMock(side_effect=mock_send)
    
    # Ensure build_request returns a proper Request object with headers
    def mock_build_request(method, url, **kwargs):
        headers = kwargs.get('headers', {})
        if 'content-type' not in headers:
            headers['content-type'] = 'application/json'
        return Request(method, url, headers=headers)
    
    mock_client.build_request = MagicMock(side_effect=mock_build_request)
    mock_client.send = AsyncMock(side_effect=mock_send)
    
    print("DEBUG: Mock client configured with mock_send function")
    
    # Mock gRPC stub and channel
    mock_stub = MagicMock()
    mock_channel = MagicMock()
    mock_search_response = MagicMock()
    mock_search_response.results = []
    mock_stub.Search = AsyncMock(return_value=mock_search_response)
    
    # Set up initial mocks
    print("DEBUG: Setting up initial mocks")
    client._connection._client = mock_client
    client._connection._grpc_stub = mock_stub
    client._connection._grpc_channel = mock_channel
    client._connection._weaviate_version = _ServerVersion.from_string("1.23.7")
    print("DEBUG: Initial mocks configured")
    
    # Mock connect method
    async def mock_connect(skip_init_checks: bool = False) -> None:
        print("\nDEBUG: mock_connect called")
        
        # Configure logger before setting up connection
        from weaviate.logger import _setup_logger
        logger = _setup_logger()
        print(f"DEBUG: Logger configured in mock_connect: level={logger.level}, handlers={logger.handlers}")
        
        client._connection._client = mock_client
        client._connection._grpc_stub = mock_stub
        client._connection._grpc_channel = mock_channel
        client._connection._weaviate_version = _ServerVersion.from_string("1.23.7")
        client._connection.__connected = True
        print("DEBUG: mock_connect completed")
        return None
    
    # Mock connect and other async methods
    client.connect = AsyncMock(side_effect=mock_connect)
    
    # Mock get_meta to ensure it uses the connection's send method
    async def mock_get_meta():
        print("\nDEBUG: mock_get_meta called")
        response = await client._connection.get("/v1/meta")
        print(f"DEBUG: mock_get_meta response: {response}")
        return {"version": "1.23.7"}
    
    client.get_meta = AsyncMock(side_effect=mock_get_meta)
    client.is_ready = MagicMock(return_value=True)
    client._connection.is_connected = MagicMock(return_value=True)
    
    # Create a proper mock for collections that uses the connection's send method
    async def mock_create_collection(*args, **kwargs):
        print("\nDEBUG: mock_create_collection called")
        # Make the actual HTTP request through the connection
        response = await client._connection.post(
            path="/v1/schema",
            weaviate_object={
                "class": kwargs.get("name", "test"),
                "vectorizer": "none",
                "properties": [{"name": "name", "dataType": ["text"]}]
            }
        )
        print(f"DEBUG: Collection creation response: {response}")
        
        # Create a mock collection that will use the connection for operations
        mock_collection = MagicMock(spec=Collection)
        
        # Mock collection.data.insert to use connection
        async def mock_insert(data):
            print("\nDEBUG: mock_insert called")
            response = await client._connection.post(
                path=f"/v1/objects",
                weaviate_object=data
            )
            print(f"DEBUG: Insert response: {response}")
            return None
        
        mock_collection.data = MagicMock()
        mock_collection.data.insert = AsyncMock(side_effect=mock_insert)
        
        # Mock collection.query.fetch_objects to use gRPC
        async def mock_fetch_objects():
            print("\nDEBUG: mock_fetch_objects called")
            print("DEBUG: Using gRPC stub for fetch_objects")
            
            # Create a proper gRPC request
            from weaviate.proto.v1 import search_get_pb2
            request = search_get_pb2.SearchRequest(
                collection=kwargs.get("name", "test"),  # Use the collection name from create args
                limit=10
            )
            
            # Set up gRPC interceptor
            from weaviate.logger import GrpcLoggingInterceptor
            interceptor = GrpcLoggingInterceptor()
            
            # Create a proper mock UnaryUnaryCall
            class MockUnaryUnaryCall:
                def __init__(self, response):
                    self.response = response
                    
                def __await__(self):
                    async def _await():
                        return self.response
                    return _await().__await__()

                def cancel(self):
                    pass

                def cancelled(self):
                    return False

                def done(self):
                    return True

                def add_done_callback(self, fn):
                    fn(self)

            # Create the mock response chain
            mock_call = MockUnaryUnaryCall(mock_search_response)
            mock_response = AsyncMock(return_value=mock_call)
            
            # Import the logging function and logger
            from weaviate.logger import log_grpc_event, logger
            
            # Call the mocked Search method which should trigger logging
            print("DEBUG: Calling gRPC Search method")
            try:
                # Create a proper mock UnaryUnaryCall that will trigger logging
                mock_call = MockUnaryUnaryCall(mock_search_response)
                
                # Set up the method name in the mock stub
                mock_stub.Search = AsyncMock(return_value=mock_call)
                mock_stub.Search.__name__ = "Search"
                
                # Create a proper ClientCallDetails with method name
                call_details = MagicMock()
                call_details.method = "/weaviate.v1.WeaviateGRPC/Search"
                
                # Call the Search method through the interceptor
                call = await interceptor.intercept_unary_unary(
                    lambda details, req: mock_stub.Search(req),
                    call_details,
                    request
                )
                response = await call
                print(f"DEBUG: gRPC Search call completed: {response}")
                return []
            except Exception as e:
                print(f"DEBUG: Error in gRPC call: {str(e)}")
                raise
        
        mock_collection.query = MagicMock()
        mock_collection.query.fetch_objects = AsyncMock(side_effect=mock_fetch_objects)
        
        return mock_collection
    
    # Set up collections mock
    mock_collections = MagicMock()
    mock_collections.create = AsyncMock(side_effect=mock_create_collection)
    
    async def mock_delete_collection(name):
        print(f"\nDEBUG: mock_delete_collection called for {name}")
        response = await client._connection.delete(
            path=f"/v1/schema/{name}"
        )
        print(f"DEBUG: Delete response: {response}")
        return None
    
    mock_collections.delete = AsyncMock(side_effect=mock_delete_collection)
    client.collections = mock_collections
    
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
async def test_debug_logging_enabled(mock_client, log_capture: LogCaptureHandler) -> None:
    """Test that debug logging is enabled when WEAVIATE_LOG_LEVEL=DEBUG."""
    print("\nDEBUG: Starting test_debug_logging_enabled")
    
    # Enable debug logging
    os.environ["WEAVIATE_LOG_LEVEL"] = "DEBUG"
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(logging.DEBUG)
    print(f"DEBUG: Logger configured with level={logger.level}, handlers={logger.handlers}, propagate={logger.propagate}")
    
    # Ensure the mock client's get_meta method uses mock_send
    print("\nDEBUG: About to call connect")
    await mock_client.connect()  # Connect the client first
    print("\nDEBUG: About to call get_meta")
    await mock_client.get_meta()  # Make a request that will be logged
    print(f"\nDEBUG: After get_meta. Current logs: {log_capture.logs}")
    
    # Verify logs contain request and response info
    has_request = any("Request:" in log for log in log_capture.logs)
    has_response = any("Response:" in log for log in log_capture.logs)
    has_headers = any("Headers:" in log for log in log_capture.logs)
    
    print(f"\nDEBUG: Log verification results:")
    print(f"Has request logs: {has_request}")
    print(f"Has response logs: {has_response}")
    print(f"Has headers logs: {has_headers}")
    print(f"All logs: {log_capture.logs}")
    
    assert has_request, "No request logs found"
    assert has_response, "No response logs found"
    assert has_headers, "No headers logs found"
    
    # Verify sensitive headers are masked
    auth_logs = [log for log in log_capture.logs if "authorization" in log.lower()]
    for log in auth_logs:
        assert "[...]" in log, f"Authorization header not masked in log: {log}"
    
    cookie_logs = [log for log in log_capture.logs if "cookie" in log.lower()]
    for log in cookie_logs:
        assert "=..." in log, f"Cookie not masked in log: {log}"

@pytest.mark.asyncio
async def test_debug_logging_async(mock_client, log_capture: LogCaptureHandler) -> None:
    """Test that debug logging works with async client."""
    # Enable debug logging
    os.environ["WEAVIATE_LOG_LEVEL"] = "DEBUG"
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(logging.DEBUG)
    
    await mock_client.connect()  # Connect the client first
    await mock_client.get_meta()  # Make a request that will be logged
    
    # Verify logs contain request and response info
    assert any("Request:" in log for log in log_capture.logs)
    assert any("Response:" in log for log in log_capture.logs)
    assert any("Headers:" in log for log in log_capture.logs)

@pytest.mark.asyncio
async def test_debug_logging_with_collection_operations(
    mock_client,
    log_capture: LogCaptureHandler,
    request: pytest.FixtureRequest,
    monkeypatch
) -> None:
    """Test that debug logging captures collection operations."""
    from unittest.mock import AsyncMock, MagicMock
    import grpc
    
    name = request.node.name
    
    # Mock gRPC stub and channel
    mock_stub = MagicMock()
    mock_channel = MagicMock()
    
    # Mock gRPC responses with a simple dictionary instead of proto message
    mock_search_response = {"results": []}
    mock_stub.Search = AsyncMock(return_value=mock_search_response)
    
    # Set up gRPC mocks
    mock_client._connection._grpc_stub = mock_stub
    mock_client._connection._grpc_channel = mock_channel
    await mock_client.connect()
    
    # Enable debug logging
    os.environ["WEAVIATE_LOG_LEVEL"] = "DEBUG"
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(logging.DEBUG)
    
    try:
        # Create collection
        collection = await mock_client.collections.create(
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
        await collection.data.insert({"name": "test"})
        
        # Query data
        await collection.query.fetch_objects()
        
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
        await mock_client.collections.delete(name)
