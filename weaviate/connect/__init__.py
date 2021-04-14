"""
Module communication to a weaviate instance. Used to connect to
weaviate and run REST requests.
"""

__all__ = ['Connection']

from .connection import Connection
from .constants import *
