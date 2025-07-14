from typing import TypedDict

from pydantic import BaseModel


class AliasReturn(BaseModel):
    """Returned aliases from Weaviate."""

    alias: str
    collection: str


_WeaviateAlias = TypedDict("_WeaviateAlias", {"alias": str, "class": str})
