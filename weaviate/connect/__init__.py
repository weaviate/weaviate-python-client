"""
Module communication to a Weaviate instance. Used to connect to
Weaviate and run REST requests.
"""

from .base import ConnectionParams, ProtocolParams
from .v3 import Connection
from .v4 import ConnectionV4

__all__ = [
    "Connection",
    "ConnectionParams",
    "ConnectionV4",
    "ProtocolParams",
]
