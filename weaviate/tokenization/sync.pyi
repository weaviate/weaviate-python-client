from typing import Dict, List, Optional

from weaviate.collections.classes.config import (
    StopwordsCreate,
    TextAnalyzerConfigCreate,
    Tokenization,
)
from weaviate.connect.v4 import ConnectionSync
from weaviate.tokenization.models import TokenizeResult

from .executor import _TokenizationExecutor

class _Tokenization(_TokenizationExecutor[ConnectionSync]):
    def text(
        self,
        text: str,
        tokenization: Tokenization,
        *,
        analyzer_config: Optional[TextAnalyzerConfigCreate] = None,
        stopwords: Optional[StopwordsCreate] = None,
        stopword_presets: Optional[Dict[str, List[str]]] = None,
    ) -> TokenizeResult: ...
