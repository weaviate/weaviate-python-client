"""Tokenize executor."""

from typing import Any, Dict, Generic, Optional

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
        tokenization: Tokenization,
        *,
        analyzer_config: Optional[_TextAnalyzerConfigCreate] = None,
        stopword_presets: Optional[Dict[str, _StopwordsCreate]] = None,
    ) -> executor.Result[TokenizeResult]:
        """Tokenize text using the generic /v1/tokenize endpoint.

        Args:
            text: The text to tokenize.
            tokenization: The tokenization method to use (e.g. Tokenization.WORD).
            analyzer_config: Text analyzer settings (ASCII folding, stopword preset).
            stopword_presets: Custom stopword preset definitions, keyed by name.
                Each value is a ``_StopwordsCreate`` with optional preset, additions,
                and removals fields.

        Returns:
            A TokenizeResult with indexed and query token lists.

        Raises:
            WeaviateUnsupportedFeatureError: If the server version is below 1.37.0.
        """
        self._check_version()

        payload: Dict[str, Any] = {
            "text": text,
            "tokenization": tokenization.value,
        }

        if analyzer_config is not None:
            ac_dict = analyzer_config._to_dict()
            if ac_dict:
                payload["analyzerConfig"] = ac_dict

        if stopword_presets is not None:
            payload["stopwordPresets"] = {
                name: cfg._to_dict() for name, cfg in stopword_presets.items()
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
            return TokenizeResult.model_validate(response.json())

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=path,
            weaviate_object=payload,
            error_msg="Property tokenization failed",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="tokenize property text"),
        )
