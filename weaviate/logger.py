import json
import logging
import os
import textwrap
from typing import Any, Awaitable, AsyncIterable, Callable, Coroutine, Dict, Optional, Sequence, TypeVar, Union, cast

import grpc
import httpx
from grpc.aio import (
    StreamStreamCall,
    StreamUnaryCall,
    UnaryStreamCall,
    UnaryUnaryCall,
)


def _setup_logger() -> logging.Logger:
    """Set up the weaviate-client logger with proper configuration."""
    # Get and validate log level from environment
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    log_level = os.getenv("WEAVIATE_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level) if log_level in valid_levels else logging.INFO

    # Configure root logger first to ensure proper propagation
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Always set root to DEBUG for proper propagation

    # Configure weaviate-client logger
    logger = logging.getLogger("weaviate-client")
    logger.setLevel(level)

    # Only add handler if none exist (prevents duplicate handlers)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    # Always enable propagation for test capture
    logger.propagate = True

    return logger


# Initialize logger
logger = _setup_logger()


def _mask_sensitive_headers(headers: Dict[str, str], is_response: bool = False) -> Dict[str, str]:
    """Mask sensitive information in headers like authorization tokens and cookies.

    This function masks:
    - Authorization headers and values
    - API keys
    - Tokens and secrets
    - Cookie values (request only)
    - Set-Cookie values (response only)
    - Access-Control-Allow-Headers containing authorization

    Args:
        headers: Dictionary of headers to mask
        is_response: Whether these are response headers (affects cookie masking)

    Returns:
        Dictionary with sensitive headers masked
    """
    masked = {}
    sensitive_patterns = ["authorization", "api-key", "api_key", "token", "secret"]

    for key, value in headers.items():
        key_lower = key.lower()

        # Mask sensitive headers and values
        if any(pattern in key_lower for pattern in sensitive_patterns):
            masked[key] = "[...]"
        # Mask cookies in requests and responses
        elif key_lower in ["cookie", "set-cookie"]:
            # Split on first = and mask everything after
            masked[key] = value.split("=")[0] + "=..."
        # Mask CORS headers listing authorization
        elif "access-control-allow-headers" in key_lower and "authorization" in value.lower():
            masked[key] = "[...]"
        # Keep non-sensitive headers as-is
        else:
            masked[key] = value

    return masked


async def log_http_event(response: httpx.Response) -> None:
    """Log HTTP request and response details using the default logger.

    This function logs both the request and response details when WEAVIATE_LOG_LEVEL=DEBUG,
    including:
    - Request method and URL
    - Request headers (with sensitive information masked)
    - Request body (if present, formatted as JSON when possible)
    - Response status code
    - Response headers (with sensitive information masked)
    - Response body (if present, formatted as JSON when possible)

    Args:
        response: The httpx Response object containing both request and response info
    """
    # Get the current logger instance to ensure we have the latest configuration
    current_logger = logging.getLogger("weaviate-client")
    if current_logger.getEffectiveLevel() > logging.DEBUG:
        return

    request = response.request

    # Build log message parts
    log_parts = []

    # Request section
    log_parts.append(f"Request: {request.method} {request.url}")
    log_parts.append("Headers:")
    for key, value in _mask_sensitive_headers(dict(request.headers)).items():
        log_parts.append(f"  {key}: {value}")

    # Safely check if request has content
    try:
        if hasattr(request, "content") and request.content:
            log_parts.append("Body:")
            try:
                body = json.loads(request.content)
                formatted_body = json.dumps(body, indent=2)
                for line in formatted_body.split("\n"):
                    log_parts.append(f"  {line}")
            except json.JSONDecodeError:
                content = request.content.decode(errors="ignore")
                for line in content.split("\n"):
                    if line.strip():  # Skip empty lines
                        log_parts.append(f"  {line}")
    except Exception:
        # If we can't access content safely, just skip body logging
        log_parts.append("Body: <unavailable>")

    # Response section
    log_parts.append(f"Response: status_code={response.status_code}")
    log_parts.append("Headers:")
    for key, value in _mask_sensitive_headers(dict(response.headers), is_response=True).items():
        log_parts.append(f"  {key}: {value}")

    # Safely check if response has content and is not a streaming response
    try:
        if hasattr(response, "_content") and response._content:
            log_parts.append("Body:")
            try:
                body = response.json()
                formatted_body = json.dumps(body, indent=2)
                for line in formatted_body.split("\n"):
                    log_parts.append(f"  {line}")
            except (json.JSONDecodeError, ValueError):
                content = response.text
                for line in content.split("\n"):
                    if line.strip():  # Skip empty lines
                        log_parts.append(f"  {line}")
    except Exception:
        # If we can't access content safely, just skip body logging
        log_parts.append("Body: <streaming or unavailable>")

    # Log everything as a single message
    logger.debug("\n".join(log_parts))


def log_grpc_event(method_name: str, request: Any, response: Any) -> None:
    """Log gRPC request and response details using the default logger.

    Args:
        method_name: Name of the gRPC method being called
        request: The gRPC request object or "stream" for streaming requests
        response: The gRPC response object, or None for streaming responses
    """
    if logger.getEffectiveLevel() > logging.DEBUG:
        return

    # Log request
    logger.debug("==================== gRPC Request ====================")
    logger.debug(f"Method: {method_name}")
    logger.debug("Request:")
    logger.debug(textwrap.indent(str(request), "  "))

    # Log response if present
    if response is not None:
        logger.debug("==================== gRPC Response ===================")
        logger.debug("Response:")
        logger.debug(textwrap.indent(str(response), "  "))
        logger.debug("====================================================")


T = TypeVar('T')
S = TypeVar('S')

class GrpcLoggingInterceptor(
    grpc.aio.UnaryUnaryClientInterceptor,
    grpc.aio.UnaryStreamClientInterceptor,
    grpc.aio.StreamUnaryClientInterceptor,
    grpc.aio.StreamStreamClientInterceptor,
):
    """Interceptor that logs gRPC requests and responses when WEAVIATE_LOG_LEVEL=DEBUG.

    This interceptor handles all four types of gRPC calls:
    - Unary-unary: Single request, single response
    - Unary-stream: Single request, stream of responses
    - Stream-unary: Stream of requests, single response
    - Stream-stream: Stream of requests, stream of responses

    For streaming operations, the request is logged as "stream" and response may be None.
    """

    def _get_method_name(self, client_call_details: grpc.aio.ClientCallDetails) -> str:
        """Extract the method name from the full gRPC method path.

        Args:
            client_call_details: Contains the full method path (e.g., "/package.Service/Method")

        Returns:
            The method name portion of the path (e.g., "Method")
        """
        # Decode bytes to string if needed
        method = client_call_details.method
        if isinstance(method, bytes):
            method = method.decode("utf-8")

        # Ensure we're returning a string
        method_str = str(method)
        return method_str.split("/")[-1] if "/" in method_str else method_str

    async def intercept_unary_unary(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, Any], UnaryUnaryCall],
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> UnaryUnaryCall:
        """Intercept and log unary-unary gRPC calls (single request, single response)."""
        call = await continuation(client_call_details, request)
        response = await call
        log_grpc_event(self._get_method_name(client_call_details), request, response)
        return cast(UnaryUnaryCall, call)

    async def intercept_unary_stream(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, Any], UnaryStreamCall],
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> UnaryStreamCall:
        """Intercept and log unary-stream gRPC calls (single request, stream response)."""
        # Cast the continuation result to Awaitable to satisfy mypy
        call = cast(Awaitable[UnaryStreamCall], continuation(client_call_details, request))
        result = await call
        # Don't await streaming calls
        log_grpc_event(self._get_method_name(client_call_details), request, None)
        return cast(UnaryStreamCall, result)

    async def intercept_stream_unary(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, Any], StreamUnaryCall],
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: Any,
    ) -> Union[AsyncIterable[Any], UnaryStreamCall]:
        """Intercept and log stream-unary gRPC calls (stream request, single response)."""
        call = await continuation(client_call_details, request_iterator)
        response = await call
        log_grpc_event(self._get_method_name(client_call_details), "stream", response)
        return cast(Union[AsyncIterable[Any], UnaryStreamCall], call)

    async def intercept_stream_stream(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, Any], StreamStreamCall],
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: Any,
    ) -> StreamStreamCall:
        """Intercept and log stream-stream gRPC calls (stream request, stream response)."""
        # Cast the continuation result to Awaitable to satisfy mypy
        call = cast(Awaitable[StreamStreamCall], continuation(client_call_details, request_iterator))
        result = await call
        # Don't await streaming calls
        log_grpc_event(self._get_method_name(client_call_details), "stream", None)
        return cast(StreamStreamCall, result)
