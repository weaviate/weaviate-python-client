"""
Module communication to a Weaviate instance. Used to connect to
Weaviate and run REST requests.
"""

from .connection import Connection, GRPCConnection
from .httpx_connection import HttpxConnection

__all__ = ["Connection", "GRPCConnection", "HttpxConnection"]
