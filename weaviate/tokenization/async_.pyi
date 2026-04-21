from typing import Dict, List, Optional, overload

from weaviate.collections.classes.config import (
    StopwordsCreate,
    TextAnalyzerConfigCreate,
    Tokenization,
)
from weaviate.connect.v4 import ConnectionAsync
from weaviate.tokenization.models import TokenizeResult

from .executor import _TokenizationExecutor

class _TokenizationAsync(_TokenizationExecutor[ConnectionAsync]):
    @overload
    async def text(
        self,
        text: str,
        tokenization: Tokenization,
        *,
        analyzer_config: Optional[TextAnalyzerConfigCreate] = ...,
        stopwords: Optional[StopwordsCreate] = ...,
    ) -> TokenizeResult: ...
    @overload
    async def text(
        self,
        text: str,
        tokenization: Tokenization,
        *,
        analyzer_config: Optional[TextAnalyzerConfigCreate] = ...,
        stopword_presets: Optional[Dict[str, List[str]]] = ...,
    ) -> TokenizeResult: ...
