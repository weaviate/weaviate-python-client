import os
import json
import textwrap
from logging import getLogger
from typing import Dict, Any

import httpx

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
    request = response.request
    
    # Log request details
    logger.debug(f"Request: {request.method} {request.url}")
    logger.debug("  Headers:")
    masked_req_headers = _mask_sensitive_headers(dict(request.headers))
    for key, value in masked_req_headers.items():
        logger.debug(f"    {key}: {value}")
    
    # Log request body if present
    if request.content:
        logger.debug("  Body:")
        try:
            request_body = json.loads(request.content)
            logger.debug(
                textwrap.indent(
                    json.dumps(request_body, indent=2),
                    "    "
                )
            )
        except json.JSONDecodeError:
            logger.debug(textwrap.indent(request.content.decode(errors="ignore"), "    "))
    
    # Log response details
    logger.debug(f"Response: status_code={response.status_code}")
    logger.debug("  Headers:")
    masked_resp_headers = _mask_sensitive_headers(dict(response.headers), is_response=True)
    for key, value in masked_resp_headers.items():
        logger.debug(f"    {key}: {value}")
