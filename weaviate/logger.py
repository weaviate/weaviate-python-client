import os
import json
import logging
import textwrap
from typing import Dict, Any, Optional, Union, Callable

import httpx
import grpc
from grpc.aio import UnaryUnaryCall, UnaryStreamCall, StreamUnaryCall, StreamStreamCall  # type: ignore

def _setup_logger():
    """Set up the weaviate-client logger with proper configuration."""
    logger = logging.getLogger("weaviate-client")
    log_level = os.getenv("WEAVIATE_LOG_LEVEL", "INFO")
    logger.setLevel(getattr(logging, log_level))
    logger.propagate = True  # Ensure log propagation is enabled
    
    # Add a StreamHandler if none exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, log_level))
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    print(f"DEBUG: Logger initialized with level {logger.level}, handlers: {logger.handlers}")
    return logger

logger = _setup_logger()

def _mask_sensitive_headers(headers: Dict[str, str], is_response: bool = False) -> Dict[str, str]:
    """Mask sensitive information in headers like authorization tokens and cookies.
    
    Args:
        headers: Dictionary of headers to mask
        is_response: Whether these are response headers (affects which headers to mask)
    
    Returns:
        Dictionary with sensitive headers masked
    """
    masked = {}
    for key, value in headers.items():
        key_lower = key.lower()
        if key_lower == "authorization" or "authorization" in key_lower:
            value = "[...]"
        elif key_lower == "cookie" and not is_response:
            value = value.split("=")[0] + "=..."
        elif key_lower == "set-cookie" and is_response:
            value = value.split("=")[0] + "=..."
        elif any(api_key in key_lower for api_key in ["api-key", "api_key", "token", "secret"]):
            value = "[...]"
        elif "access-control-allow-headers" in key_lower and "authorization" in value.lower():
            # Special handling for CORS headers that list Authorization
            value = "[...]"
        masked[key] = value
    return masked

def log_http_event(response: httpx.Response) -> None:
    """Log HTTP request and response details using the default logger.
    
    Args:
        response: The httpx Response object containing both request and response info
    """
    print(f"\nDEBUG: log_http_event called")
    print(f"DEBUG: Logger state: level={logger.level}, handlers={logger.handlers}, propagate={logger.propagate}")
    print(f"DEBUG: Effective level: {logger.getEffectiveLevel()}")

    if logger.getEffectiveLevel() > logging.DEBUG:
        print("DEBUG: Skipping logging due to level")
        return

    try:
        request = response.request
        print(f"DEBUG: Processing request {request.method} {request.url}")
        
        # Log request details with clear separation
        separator = "==================== HTTP Request ===================="
        print(f"DEBUG: About to log separator: {separator}")
        logger.debug(separator)
        
        request_line = f"Request: {request.method} {request.url}"
        print(f"DEBUG: About to log request line: {request_line}")
        logger.debug(request_line)
        
        print("DEBUG: About to log headers")
        logger.debug("Headers:")
        masked_req_headers = _mask_sensitive_headers(dict(request.headers))
        for key, value in masked_req_headers.items():
            header_line = f"  {key}: {value}"
            print(f"DEBUG: About to log header: {header_line}")
            logger.debug(header_line)
        
        # Log request body if present
        if request.content:
            print("DEBUG: About to log request body")
            logger.debug("Body:")
            try:
                request_body = json.loads(request.content)
                body_str = textwrap.indent(json.dumps(request_body, indent=2), "  ")
                print(f"DEBUG: About to log body: {body_str}")
                logger.debug(body_str)
            except json.JSONDecodeError:
                body_str = textwrap.indent(request.content.decode(errors="ignore"), "  ")
                print(f"DEBUG: About to log raw body: {body_str}")
                logger.debug(body_str)
        
        # Log response details with clear separation
        separator = "==================== HTTP Response ==================="
        print(f"DEBUG: About to log response separator: {separator}")
        logger.debug(separator)
        
        response_line = f"Response: status_code={response.status_code}"
        print(f"DEBUG: About to log response line: {response_line}")
        logger.debug(response_line)
        
        print("DEBUG: About to log response headers")
        logger.debug("Headers:")
        masked_resp_headers = _mask_sensitive_headers(dict(response.headers), is_response=True)
        for key, value in masked_resp_headers.items():
            header_line = f"  {key}: {value}"
            print(f"DEBUG: About to log response header: {header_line}")
            logger.debug(header_line)
        
        separator = "===================================================="
        print(f"DEBUG: About to log final separator: {separator}")
        logger.debug(separator)
        
        print("DEBUG: Finished logging HTTP event")
    except Exception as e:
        print(f"DEBUG: Error in log_http_event: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        logger.debug(f"Error logging HTTP event: {str(e)}")

def log_grpc_event(method_name: str, request: Any, response: Any) -> None:
    """Log gRPC request and response details using the default logger.
    
    Args:
        method_name: The name of the gRPC method being called
        request: The gRPC request object
        response: The gRPC response object (may be None for request-only logging)
    """
    print(f"\nDEBUG: log_grpc_event called for method {method_name}")
    print(f"DEBUG: Logger level: {logger.getEffectiveLevel()}, handlers: {logger.handlers}")
    print(f"DEBUG: Request type: {type(request)}")
    print(f"DEBUG: Response type: {type(response)}")
    if logger.getEffectiveLevel() > logging.DEBUG:
        return

    try:
        # Log request details
        logger.debug("==================== gRPC Request ====================")
        logger.debug(f"Method: {method_name}")
        logger.debug("Request:")
        try:
            logger.debug(textwrap.indent(str(request), "  "))
        except Exception as e:
            logger.debug(f"  Error logging request: {e}")
        
        # Log response details if available
        if response is not None:
            logger.debug("==================== gRPC Response ===================")
            logger.debug("Response:")
            try:
                logger.debug(textwrap.indent(str(response), "  "))
            except Exception as e:
                logger.debug(f"  Error logging response: {e}")
            logger.debug("====================================================")
    except Exception as e:
        logger.debug(f"Error logging gRPC event: {str(e)}")

class GrpcLoggingInterceptor(
    grpc.aio.UnaryUnaryClientInterceptor,
    grpc.aio.UnaryStreamClientInterceptor,
    grpc.aio.StreamUnaryClientInterceptor,
    grpc.aio.StreamStreamClientInterceptor
):
    """Interceptor that logs gRPC requests and responses."""

    async def intercept_unary_unary(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, Any], UnaryUnaryCall],
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> UnaryUnaryCall:
        """Intercept unary-unary gRPC calls."""
        method_name = client_call_details.method
        try:
            # Extract just the method name from the full path for cleaner logging
            method = method_name.split('/')[-1] if '/' in method_name else method_name
            print(f"\nDEBUG: Intercepting gRPC call for method: {method}")
            
            call = await continuation(client_call_details, request)
            response = await call
            
            # Log the gRPC event with the clean method name
            log_grpc_event(method, request, response)
            return call
        except Exception as e:
            logger.debug(f"gRPC Error in {method_name}: {e}")
            raise

    async def intercept_unary_stream(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, Any], UnaryStreamCall],
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> UnaryStreamCall:
        """Intercept unary-stream gRPC calls."""
        method_name = client_call_details.method
        try:
            call = await continuation(client_call_details, request)
            log_grpc_event(method_name, request, None)  # Log request only
            return call
        except Exception as e:
            logger.debug(f"gRPC Error in {method_name}: {e}")
            raise

    async def intercept_stream_unary(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, Any], StreamUnaryCall],
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: Any,
    ) -> StreamUnaryCall:
        """Intercept stream-unary gRPC calls."""
        method_name = client_call_details.method
        try:
            call = await continuation(client_call_details, request_iterator)
            response = await call
            log_grpc_event(method_name, "stream", response)
            return call
        except Exception as e:
            logger.debug(f"gRPC Error in {method_name}: {e}")
            raise

    async def intercept_stream_stream(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, Any], StreamStreamCall],
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: Any,
    ) -> StreamStreamCall:
        """Intercept stream-stream gRPC calls."""
        method_name = client_call_details.method
        try:
            call = await continuation(client_call_details, request_iterator)
            log_grpc_event(method_name, "stream", None)
            return call
        except Exception as e:
            logger.debug(f"gRPC Error in {method_name}: {e}")
            raise
