"""Return types for tokenization operations."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from weaviate.collections.classes.config import Tokenization


class TokenizeResult(BaseModel):
    """Result of a tokenization operation.

    Attributes:
        indexed: Tokens as they would be stored in the inverted index.
        query: Tokens as they would be used for querying (after stopword removal).
    """

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    indexed: List[str]
    query: List[str]
