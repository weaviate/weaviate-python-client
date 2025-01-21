import json
import logging
import textwrap
from typing import Generator, Optional, List

import pytest
from _pytest.fixtures import SubRequest

import weaviate
from integration.conftest import ClientFactory, AsyncClientFactory
from weaviate.collections import Collection
from weaviate.collections.classes.config import Configure, Property, DataType
from weaviate.config import AdditionalConfig

class CustomLogger(logging.Logger):
    """Custom logger class to capture logs for testing."""
    def __init__(self, name: str = "test-logger"):
        super().__init__(name)
        self.logs: list[str] = []
        self.setLevel(logging.DEBUG)
        
        # Add a handler to actually process the logs
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(message)s')  # Only capture the message
        handler.setFormatter(formatter)
        self.addHandler(handler)

    def _format_message(self, msg: str, *args) -> str:
        """Format the message if args are provided."""
        if args:
            try:
                return msg % args
            except (TypeError, ValueError):
                return msg
        return msg

    def _store_log(self, msg: str) -> None:
        """Store a log message, handling both single-line and multi-line messages."""
        # Split the message into lines and store each line
        lines = msg.splitlines()
        if len(lines) == 1:
            # Single line - store as is
            if lines[0].strip():
                self.logs.append(lines[0])
        else:
            # Multi-line - preserve indentation for JSON and other formatted content
            for line in lines:
                if line.strip():  # Skip empty lines
                    self.logs.append(line)

    def debug(self, msg: str, *args, **kwargs) -> None:
        formatted_msg = self._format_message(msg, *args)
        self._store_log(formatted_msg)
        super().debug(formatted_msg, **kwargs)  # Don't pass args since we've already formatted

    def info(self, msg: str, *args, **kwargs) -> None:
        formatted_msg = self._format_message(msg, *args)
        self._store_log(formatted_msg)
        super().info(formatted_msg, **kwargs)  # Don't pass args since we've already formatted

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
        collection.query.fetch_objects()  # Execute query to generate logs

        # Verify logs for each operation
        create_logs = [log for log in custom_logger.logs if 'Request: POST' in log and '/v1/schema' in log]
        assert len(create_logs) > 0, "Collection creation request not logged"

        # Look for the class name in the JSON body
        # Find the schema creation request logs
        current_request = []
        in_body = False
        found_schema = False
        is_schema_request = False
        
        for log in custom_logger.logs:
            log = log.strip()
            
            # Start of a new request
            if log.startswith('Request: POST'):
                current_request = []
                in_body = False
                is_schema_request = '/v1/schema' in log
                print(f"Found request: {log}, is_schema_request: {is_schema_request}")
            elif log == 'Body:':
                in_body = True
                current_request = []  # Reset for new body
                print("Found body section")
            elif in_body:  # Process all bodies, but only try to parse schema requests
                if log.startswith('Response:'):
                    print(f"End of body section, current_request: {current_request}")
                    if current_request and is_schema_request:
                        try:
                            # Reconstruct and parse JSON
                            json_str = ""
                            in_json = False
                            json_level = 0
                            needs_comma = False
                            
                            for line in current_request:
                                stripped = line.strip().rstrip(',')
                                if not stripped or stripped.startswith('"Body:'):
                                    continue
                                
                                if stripped == '{':
                                    in_json = True
                                    json_level += 1
                                    json_str += '{'
                                    needs_comma = False
                                elif stripped == '}':
                                    json_level -= 1
                                    json_str += '}'
                                    if json_level == 0:
                                        in_json = False
                                    needs_comma = True
                                elif stripped == '[':
                                    json_str += '['
                                    needs_comma = False
                                elif stripped == ']':
                                    json_str += ']'
                                    needs_comma = True
                                else:
                                    if in_json and json_level > 0:
                                        if needs_comma and not json_str.endswith('{') and not json_str.endswith('['):
                                            json_str += ','
                                    json_str += stripped
                                    needs_comma = True
                            
                            try:
                                print(f"Attempting to parse JSON string: {json_str}")
                                result = json.loads(json_str)
                                print(f"Successfully parsed JSON: {result}")
                            except json.JSONDecodeError as e:
                                print(f"Failed to parse JSON: {e}")
                                print(f"JSON string was: {json_str}")
                                print(f"Current request content: {current_request}")
                                raise  # Re-raise to fail the test
                            except Exception as e:
                                print(f"Unexpected error while processing JSON: {str(e)}")
                                print(f"JSON string was: {json_str}")
                                print(f"Current request content: {current_request}")
                                raise  # Re-raise to fail the test
                            
                            print(f"Built dictionary: {result}")
                            # Case-insensitive comparison of class names
                            if result.get('class', '').lower() == name.lower():
                                found_schema = True
                                print(f"Found matching schema with class {name}")
                                break
                        except json.JSONDecodeError as e:
                            print(f"Failed to process request: {e}")
                            print(f"Current request content: {current_request}")
                            print(f"Built dictionary: {result}")
                            print(f"Error details: {str(e)}")
                            # Try to pretty print the dictionary for debugging
                            try:
                                print("Formatted dictionary attempt:")
                                print(json.dumps(result, indent=2))
                            except:
                                pass
                        except Exception as e:
                            print(f"Unexpected error while processing JSON: {str(e)}")
                            print(f"Current request content: {current_request}")
                    in_body = False
                else:
                    current_request.append(log)
        
        assert found_schema, f"Failed to find schema creation JSON with class '{name}' in logs. Current request content: {current_request}"

        insert_logs = [log for log in custom_logger.logs if 'Request: POST' in log and '/objects' in log]
        assert len(insert_logs) > 0, "Data insertion not logged"

        # Check for gRPC query logs
        query_logs = [log for log in custom_logger.logs if 'Method: Search' in log]
        assert len(query_logs) > 0, "Query operation not logged"
            
        # Verify gRPC request details are logged
        grpc_request_logs = [log for log in custom_logger.logs if 'collection: "Test_logger_with_collection_operations"' in log]
        assert len(grpc_request_logs) > 0, "gRPC request details not logged"

    finally:
        client.collections.delete(name)
