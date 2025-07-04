from typing import TypedDict

from pydantic import BaseModel


class AliasReturn(BaseModel):
    """Return type of the backup status methods."""

    alias: str
    collection: str


_WeaviateAlias = TypedDict("_WeaviateAlias", {"alias": str, "class": str})
