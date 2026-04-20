"""Return types for tokenization operations."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from weaviate.collections.classes.config import Tokenization


class TokenizeResult(BaseModel):
    """Result of a tokenization operation.

    Attributes:
        indexed: Tokens as they would be stored in the inverted index.
        query: Tokens as they would be used for querying (after stopword removal).
        tokenization: The tokenization method that was applied. Populated only by
            the property-level endpoint, where the tokenization is resolved from
            the property's schema. The generic ``/v1/tokenize`` endpoint does not
            echo it back (the caller passed it).
    """

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    indexed: List[str]
    query: List[str]
    tokenization: Optional[Tokenization] = None
