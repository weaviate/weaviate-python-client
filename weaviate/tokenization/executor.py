"""Tokenize executor."""

from typing import Any, Dict, Generic, List, Optional, Union

from httpx import Response

from weaviate.collections.classes.config import (
    StopwordsConfig,
    StopwordsPreset,
    TextAnalyzerConfig,
    Tokenization,
    _StopwordsCreate,
    _TextAnalyzerConfigCreate,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType, _ExpectedStatusCodes
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.tokenization.models import TokenizeResult


def _parse_analyzer_config(body: Dict[str, Any]) -> Optional[TextAnalyzerConfig]:
    ac = body.get("analyzerConfig")
    if ac is None:
        return None
    if "asciiFold" not in ac and "stopwordPreset" not in ac:
        return None
    return TextAnalyzerConfig(
        ascii_fold=ac.get("asciiFold", False),
        ascii_fold_ignore=ac.get("asciiFoldIgnore"),
        stopword_preset=ac.get("stopwordPreset"),
    )


def _parse_stopword_config(body: Dict[str, Any]) -> Optional[StopwordsConfig]:
    sc = body.get("stopwordConfig")
    if sc is None:
        return None
    return StopwordsConfig(
        preset=StopwordsPreset(sc["preset"]) if sc.get("preset") else StopwordsPreset.NONE,
        additions=sc.get("additions"),
        removals=sc.get("removals"),
    )


def _parse_tokenize_result(body: Dict[str, Any]) -> TokenizeResult:
    return TokenizeResult(
        tokenization=body["tokenization"],
        indexed=body["indexed"],
        query=body["query"],
        analyzer_config=_parse_analyzer_config(body),
        stopword_config=_parse_stopword_config(body),
    )


class _TokenizationExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def _check_version(self) -> None:
        if self._connection._weaviate_version.is_lower_than(1, 37, 0):
            raise WeaviateUnsupportedFeatureError(
                "Tokenization",
                str(self._connection._weaviate_version),
                "1.37.0",
            )

    def text(
        self,
        text: str,
        tokenization: Union[Tokenization, str],
        *,
        analyzer_config: Optional[_TextAnalyzerConfigCreate] = None,
        ascii_fold: Optional[bool] = None,
        ascii_fold_ignore: Optional[List[str]] = None,
        stopword_preset: Optional[Union[StopwordsPreset, str]] = None,
        stopword_presets: Optional[Dict[str, _StopwordsCreate]] = None,
    ) -> executor.Result[TokenizeResult]:
        """Tokenize text using the generic /v1/tokenize endpoint.

        Analyzer settings can be provided either via a ``_TextAnalyzerConfigCreate``
        object **or** via the individual keyword arguments (``ascii_fold``,
        ``ascii_fold_ignore``, ``stopword_preset``).  If ``analyzer_config`` is
        given the individual keyword arguments are ignored.

        Args:
            text: The text to tokenize.
            tokenization: The tokenization method to use (e.g. Tokenization.WORD).
            analyzer_config: A ``_TextAnalyzerConfigCreate`` instance that bundles
                ascii_fold, ascii_fold_ignore, and stopword_preset settings.
            ascii_fold: Whether to fold accented characters to ASCII equivalents.
            ascii_fold_ignore: Characters to exclude from ASCII folding.
            stopword_preset: Stopword preset name to apply for query-time filtering.
            stopword_presets: Custom stopword preset definitions, keyed by name.
                Each value is a ``_StopwordsCreate`` with optional preset, additions,
                and removals fields.

        Returns:
            A TokenizeResult with indexed and query token lists.

        Raises:
            WeaviateUnsupportedFeatureError: If the server version is below 1.37.0.
        """
        self._check_version()
        tokenization_str = (
            tokenization.value if isinstance(tokenization, Tokenization) else tokenization
        )

        payload: Dict[str, Any] = {
            "text": text,
            "tokenization": tokenization_str,
        }

        if analyzer_config is not None:
            ac_dict = analyzer_config._to_dict()
            if ac_dict:
                payload["analyzerConfig"] = ac_dict
        else:
            ac: Dict[str, Any] = {}
            if ascii_fold is not None:
                ac["asciiFold"] = ascii_fold
            if ascii_fold_ignore is not None:
                ac["asciiFoldIgnore"] = ascii_fold_ignore
            if stopword_preset is not None:
                ac["stopwordPreset"] = (
                    stopword_preset.value
                    if isinstance(stopword_preset, StopwordsPreset)
                    else stopword_preset
                )
            if ac:
                payload["analyzerConfig"] = ac

        if stopword_presets is not None:
            payload["stopwordPresets"] = {
                name: cfg._to_dict() for name, cfg in stopword_presets.items()
            }

        def resp(response: Response) -> TokenizeResult:
            return _parse_tokenize_result(response.json())

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path="/tokenize",
            weaviate_object=payload,
            error_msg="Tokenization failed",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="tokenize text"),
        )

    def for_property(
        self,
        collection_name: str,
        property_name: str,
        text: str,
    ) -> executor.Result[TokenizeResult]:
        """Tokenize text using a property's configured tokenization settings.

        Args:
            collection_name: The collection (class) name.
            property_name: The property name whose tokenization config to use.
            text: The text to tokenize.

        Returns:
            A TokenizeResult with indexed and query token lists.

        Raises:
            WeaviateUnsupportedFeatureError: If the server version is below 1.37.0.
        """
        self._check_version()
        path = f"/schema/{collection_name}/properties/{property_name}/tokenize"

        payload: Dict[str, Any] = {"text": text}

        def resp(response: Response) -> TokenizeResult:
            return _parse_tokenize_result(response.json())

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=path,
            weaviate_object=payload,
            error_msg="Property tokenization failed",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="tokenize property text"),
        )
