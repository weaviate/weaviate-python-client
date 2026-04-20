from typing import Dict, Optional

from weaviate.collections.classes.config import (
    Tokenization,
    _StopwordsCreate,
    _TextAnalyzerConfigCreate,
)
from weaviate.connect.v4 import ConnectionAsync
from weaviate.tokenization.models import TokenizeResult

from .executor import _TokenizationExecutor

class _TokenizationAsync(_TokenizationExecutor[ConnectionAsync]):
    async def text(
        self,
        text: str,
        tokenization: Tokenization,
        *,
        analyzer_config: Optional[_TextAnalyzerConfigCreate] = None,
        stopword_presets: Optional[Dict[str, _StopwordsCreate]] = None,
    ) -> TokenizeResult: ...
