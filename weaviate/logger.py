import os
import json
import textwrap
from logging import getLogger
from typing import Dict, Any, Optional, Union

import httpx
import grpc
from grpc.aio import UnaryUnaryCall, UnaryStreamCall, StreamUnaryCall, StreamStreamCall  # type: ignore

logger = getLogger("weaviate-client")
logger.setLevel(os.getenv("WEAVIATE_LOG_LEVEL", "INFO"))

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
        if key_lower == "authorization":
            value = "[...]"
        elif key_lower == "cookie" and not is_response:
            value = value.split("=")[0] + "=..."
        elif key_lower == "set-cookie" and is_response:
            value = value.split("=")[0] + "=..."
        masked[key] = value
    return masked

def log_http_event(logger: Any, response: httpx.Response) -> None:
    """Log HTTP request and response details using the provided logger.
    
    Args:
        logger: Logger object to use for logging (must support debug method)
        response: The httpx Response object containing both request and response info
    """
    print("DEBUG: log_http_event called with logger:", logger)
    try:
        request = response.request
        
        # Log request details with clear separation
        logger.debug("==================== HTTP Request ====================")
        logger.debug(f"Request: {request.method} {request.url}")
        logger.debug("Headers:")
        masked_req_headers = _mask_sensitive_headers(dict(request.headers))
        for key, value in masked_req_headers.items():
            logger.debug(f"  {key}: {value}")
        
        # Log request body if present
        if request.content:
            logger.debug("Body:")
            try:
                request_body = json.loads(request.content)
                logger.debug(
                    textwrap.indent(
                        json.dumps(request_body, indent=2),
                        "  "
                    )
                )
            except json.JSONDecodeError:
                logger.debug(textwrap.indent(request.content.decode(errors="ignore"), "  "))
        
        # Log response details with clear separation
        logger.debug("==================== HTTP Response ===================")
        logger.debug(f"Response: status_code={response.status_code}")
        logger.debug("Headers:")
        masked_resp_headers = _mask_sensitive_headers(dict(response.headers), is_response=True)
        for key, value in masked_resp_headers.items():
            logger.debug(f"  {key}: {value}")
        logger.debug("====================================================")
    except Exception as e:
        logger.debug(f"Error logging HTTP event: {str(e)}")

def log_grpc_event(logger: Any, method_name: str, request: Any, response: Any) -> None:
    """Log gRPC request and response details.
    
    Args:
        logger: Logger object to use for logging (must support debug method)
        method_name: The name of the gRPC method being called
        request: The gRPC request object
        response: The gRPC response object (may be None for request-only logging)
    """
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

async def grpc_logging_interceptor(
    continuation: Any,
    client_call_details: grpc.aio.ClientCallDetails,
    request: Any,
    logger: Optional[Any] = None,
) -> Union[UnaryUnaryCall, UnaryStreamCall, StreamUnaryCall, StreamStreamCall]:
    """gRPC interceptor for logging requests and responses.
    
    Args:
        continuation: The RPC continuation function
        client_call_details: Contains RPC method details
        request: The request being made
        logger: Optional logger to use for logging
    
    Returns:
        The result of the RPC call
    """
    if logger is None:
        return await continuation(client_call_details, request)
    
    method_name = client_call_details.method
    try:
        call = await continuation(client_call_details, request)
        response = await call
        log_grpc_event(logger, method_name, request, response)
        return call
    except Exception as e:
        if logger:
            logger.debug(f"gRPC Error in {method_name}: {e}")
        raise
