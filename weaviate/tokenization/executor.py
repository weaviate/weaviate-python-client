"""Tokenize executor."""

from typing import Any, Dict, Generic, List, Optional

from httpx import Response

from weaviate.collections.classes.config import (
    Tokenization,
    _StopwordsCreate,
    _TextAnalyzerConfigCreate,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType, _ExpectedStatusCodes
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.tokenization.models import TokenizeResult


class _TokenizationExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def __check_version(self) -> None:
        if self._connection._weaviate_version.is_lower_than(1, 37, 0):
            raise WeaviateUnsupportedFeatureError(
                "Tokenization",
                str(self._connection._weaviate_version),
                "1.37.0",
            )

    def text(
        self,
        text: str,
        tokenization: Tokenization,
        *,
        analyzer_config: Optional[_TextAnalyzerConfigCreate] = None,
        stopwords: Optional[_StopwordsCreate] = None,
        stopword_presets: Optional[Dict[str, List[str]]] = None,
    ) -> executor.Result[TokenizeResult]:
        """Tokenize text using the generic /v1/tokenize endpoint.

        For ``word`` tokenization the server defaults to the built-in ``en``
        stopword preset when no stopword configuration is supplied. Pass
        ``analyzer_config=TextAnalyzerConfig(stopword_preset="none")`` or
        equivalent to opt out.

        Args:
            text: The text to tokenize.
            tokenization: The tokenization method to use (e.g. Tokenization.WORD).
            analyzer_config: Text analyzer settings (ASCII folding, stopword
                preset name). ``stopword_preset`` may reference a built-in preset
                (``en`` / ``none``) or a name defined in ``stopword_presets``.
            stopwords: Fallback stopword config applied when
                ``analyzer_config.stopword_preset`` is not set. Same shape as a
                collection's ``invertedIndexConfig.stopwords`` — a base preset
                optionally tweaked with ``additions`` / ``removals``. An empty
                ``preset`` defaults to ``en``.
            stopword_presets: User-defined named stopword presets, each a plain
                list of words. A name matching a built-in (``en`` / ``none``)
                replaces the built-in entirely.

        Note:
            ``stopwords`` and ``stopword_presets`` are mutually exclusive on the
            server — pass one or the other, not both. The server returns HTTP
            422 if both are supplied.

        Returns:
            A TokenizeResult with indexed and query token lists. The generic
            endpoint does not echo request fields (tokenization, analyzer_config,
            stopwords, stopword_presets) back in the response.

        Raises:
            WeaviateUnsupportedFeatureError: If the server version is below 1.37.0.
            ValueError: If both ``stopwords`` and ``stopword_presets`` are passed.
        """
        self.__check_version()

        if stopwords is not None and stopword_presets is not None:
            raise ValueError("stopwords and stopword_presets are mutually exclusive; pass only one")

        payload: Dict[str, Any] = {
            "text": text,
            "tokenization": tokenization.value,
        }

        if analyzer_config is not None:
            ac_dict = analyzer_config._to_dict()
            if ac_dict:
                payload["analyzerConfig"] = ac_dict

        if stopwords is not None:
            sw_dict = stopwords._to_dict()
            if sw_dict:
                payload["stopwords"] = sw_dict

        if stopword_presets is not None:
            # Plain word-list shape matching a collection's
            # invertedIndexConfig.stopwordPresets.
            payload["stopwordPresets"] = {
                name: list(words) for name, words in stopword_presets.items()
            }

        def resp(response: Response) -> TokenizeResult:
            return TokenizeResult.model_validate(response.json())

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path="/tokenize",
            weaviate_object=payload,
            error_msg="Tokenization failed",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="tokenize text"),
        )
