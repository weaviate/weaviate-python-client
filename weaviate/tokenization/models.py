"""Return types for tokenize operations."""

from dataclasses import dataclass, field
from typing import List, Optional

from weaviate.collections.classes.config import StopwordsConfig, TextAnalyzerConfig


@dataclass
class TokenizeResult:
    """Result of a tokenization operation.

    Attributes:
        tokenization: The tokenization method that was applied.
        indexed: Tokens as they would be stored in the inverted index.
        query: Tokens as they would be used for querying (after stopword removal).
        analyzer_config: The text analyzer configuration that was used, if any.
        stopword_config: The stopword configuration that was used, if any.
    """

    tokenization: str
    indexed: List[str]
    query: List[str]
    analyzer_config: Optional[TextAnalyzerConfig] = field(default=None)
    stopword_config: Optional[StopwordsConfig] = field(default=None)
