"""
Module communication to a Weaviate instance. Used to connect to
Weaviate and run REST requests.
"""

from .base import ConnectionParams, ProtocolParams

__all__ = [
    "ConnectionParams",
    "ProtocolParams",
]
