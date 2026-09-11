"""Return types for tokenization operations."""

from typing import List

from pydantic import BaseModel


class TokenizeResult(BaseModel):
    """Result of a tokenization operation.

    Attributes:
        indexed: Tokens as they would be stored in the inverted index.
        query: Tokens as they would be used for querying (after stopword removal).
    """

    indexed: List[str]
    query: List[str]
