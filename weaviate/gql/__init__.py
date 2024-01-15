"""
GraphQL module used to create `get` and/or `aggregate`  GraphQL requests from Weaviate.
"""

__all__ = ["AdditionalProperties", "LinkTo", "Query"]

from .get import AdditionalProperties, LinkTo
from .query import Query
