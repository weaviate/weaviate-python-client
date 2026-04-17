"""Return types for tokenization operations."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from weaviate.collections.classes.config import (
    StopwordsConfig,
    StopwordsPreset,
    TextAnalyzerConfig,
    Tokenization,
)


class TokenizeResult(BaseModel):
    """Result of a tokenization operation.

    Attributes:
        tokenization: The tokenization method that was applied.
        indexed: Tokens as they would be stored in the inverted index.
        query: Tokens as they would be used for querying (after stopword removal).
        analyzer_config: The text analyzer configuration that was used, if any.
        stopword_config: The stopword configuration that was used, if any.
    """

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    tokenization: Tokenization
    indexed: List[str]
    query: List[str]
    analyzer_config: Optional[TextAnalyzerConfig] = Field(default=None, alias="analyzerConfig")
    stopword_config: Optional[StopwordsConfig] = Field(default=None, alias="stopwordConfig")

    @field_validator("analyzer_config", mode="before")
    @classmethod
    def _parse_analyzer_config(cls, v: Optional[Dict[str, Any]]) -> Optional[TextAnalyzerConfig]:
        if v is None:
            return None
        if "asciiFold" not in v and "stopwordPreset" not in v:
            return None
        return TextAnalyzerConfig(
            ascii_fold=v.get("asciiFold", False),
            ascii_fold_ignore=v.get("asciiFoldIgnore"),
            stopword_preset=v.get("stopwordPreset"),
        )

    @field_validator("stopword_config", mode="before")
    @classmethod
    def _parse_stopword_config(cls, v: Optional[Dict[str, Any]]) -> Optional[StopwordsConfig]:
        if v is None:
            return None
        return StopwordsConfig(
            preset=StopwordsPreset(v["preset"]),
            additions=v.get("additions"),
            removals=v.get("removals"),
        )
