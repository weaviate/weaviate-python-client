from typing import Dict, List, Optional, Union, overload

from weaviate.collections.classes.config import (
    StopwordsConfig,
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
        stopwords: Optional[Union[StopwordsCreate, StopwordsConfig]] = ...,
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
    async def for_property(
        self, collection: str, property_name: str, text: str
    ) -> TokenizeResult: ...
