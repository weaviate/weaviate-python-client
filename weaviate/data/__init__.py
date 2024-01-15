"""
Data module used to create, read, update and delete object and references.
"""

__all__ = ["DataObject", "ConsistencyLevel"]

from .crud_data import DataObject
from .replication import ConsistencyLevel
