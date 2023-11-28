"""
Module communication to a Weaviate instance. Used to connect to
Weaviate and run REST requests.
"""

__all__ = ["Connection", "HttpxConnection"]

from .connection import Connection
from .httpx_connection import HttpxConnection
