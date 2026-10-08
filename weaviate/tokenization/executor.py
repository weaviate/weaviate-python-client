"""Tokenize executor."""

from typing import Any, Dict, Generic, List, Optional, Union, overload

from httpx import Response

from weaviate.collections.classes.config import (
    StopwordsConfig,
    StopwordsCreate,
    TextAnalyzerConfigCreate,
    Tokenization,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType, _ExpectedStatusCodes
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.tokenization.models import TokenizeResult
from weaviate.util import _capitalize_first_letter


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

    # Overloads make ``stopwords`` and ``stopword_presets`` mutually exclusive
    # at type-check time. Passing both is additionally rejected at runtime with
    # ``ValueError`` in the implementation below. ``stopwords`` accepts either a
    # ``StopwordsCreate`` (the write-side shape) or a ``StopwordsConfig`` (the
    # read-side shape returned by ``collection.config.get()``), so values round-
    # tripped through config reads can be passed back in directly.
    @overload
    def text(
        self,
        text: str,
        tokenization: Tokenization,
        *,
        analyzer_config: Optional[TextAnalyzerConfigCreate] = ...,
        stopwords: Optional[Union[StopwordsCreate, StopwordsConfig]] = ...,
    ) -> executor.Result[TokenizeResult]: ...

    @overload
    def text(
        self,
        text: str,
        tokenization: Tokenization,
        *,
        analyzer_config: Optional[TextAnalyzerConfigCreate] = ...,
        stopword_presets: Optional[Dict[str, List[str]]] = ...,
    ) -> executor.Result[TokenizeResult]: ...

    def text(
        self,
        text: str,
        tokenization: Tokenization,
        *,
        analyzer_config: Optional[TextAnalyzerConfigCreate] = None,
        stopwords: Optional[Union[StopwordsCreate, StopwordsConfig]] = None,
        stopword_presets: Optional[Dict[str, List[str]]] = None,
    ) -> executor.Result[TokenizeResult]:
        """Tokenize text using the generic /v1/tokenize endpoint.

        For ``word`` tokenization the server defaults to the built-in ``en``
        stopword preset when no stopword configuration is supplied. Pass
        ``analyzer_config=TextAnalyzerConfigCreate(stopword_preset="none")``
        or equivalent to opt out.

        Call patterns for stopword handling (``stopwords`` and
        ``stopword_presets`` are mutually exclusive — pass at most one):

        1. **No stopword config** — rely on the server default (``en`` for
           word tokenization, none otherwise)::

               client.tokenization.text(text=..., tokenization=Tokenization.WORD)

        2. **Apply a one-off stopwords block** via ``stopwords`` — the block
           filters the query tokens directly, same shape as a collection's
           ``invertedIndexConfig.stopwords``::

               client.tokenization.text(
                   text=...,
                   tokenization=Tokenization.WORD,
                   stopwords=StopwordsCreate(preset=StopwordsPreset.EN, additions=["foo"]),
               )

        3. **Register a named-preset catalog** via ``stopword_presets`` and
           reference one by name from ``analyzer_config.stopword_preset``.
           The catalog can also override built-in presets such as ``en``::

               client.tokenization.text(
                   text=...,
                   tokenization=Tokenization.WORD,
                   analyzer_config=TextAnalyzerConfigCreate(stopword_preset="custom"),
                   stopword_presets={"custom": ["foo", "bar"]},
               )

        Args:
            text: The text to tokenize.
            tokenization: The tokenization method to use (e.g. ``Tokenization.WORD``).
            analyzer_config: Text analyzer settings (ASCII folding, stopword
                preset name), built via ``Configure.text_analyzer(...)``.
                ``stopword_preset`` may reference a built-in preset
                (``en`` / ``none``) or a name defined in ``stopword_presets``.
            stopwords: One-off stopwords block applied directly to this request.
                Mirrors the collection-level ``invertedIndexConfig.stopwords``
                shape — hence the rich model with preset / additions / removals.
                Mutually exclusive with ``stopword_presets``.
            stopword_presets: Named-preset catalog (name → word list). Mirrors
                the property-level preset catalog — a plain mapping, since a
                property only references a preset by name (via
                ``analyzer_config.stopword_preset``) rather than carrying the
                full stopwords block. Entries can override built-ins like
                ``en``. Mutually exclusive with ``stopwords``.

        Returns:
            A ``TokenizeResult`` with indexed and query token lists. The generic
            endpoint does not echo request fields back in the response.

        Raises:
            WeaviateUnsupportedFeatureError: If the server version is below 1.37.0.
            ValueError: If both ``stopwords`` and ``stopword_presets`` are passed,
                or if any ``stopword_presets`` value is not a list/tuple of strings.
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
            if isinstance(stopwords, StopwordsConfig):
                # Widen from the read-side shape returned by config.get() to the
                # write-side shape the server expects. Field parity between the
                # two classes is enforced at import time in
                # ``weaviate/collections/classes/config.py``, so iterating
                # ``StopwordsCreate.model_fields`` copies every field.
                stopwords = StopwordsCreate(
                    **{name: getattr(stopwords, name) for name in StopwordsCreate.model_fields}
                )
            sw_dict = stopwords._to_dict()
            if sw_dict:
                payload["stopwords"] = sw_dict

        if stopword_presets is not None:
            # Plain word-list shape matching a collection's
            # invertedIndexConfig.stopwordPresets. Reject str (would
            # silently split into characters) and pydantic models /
            # other non-sequence shapes up-front so callers get a clear
            # error instead of a malformed payload.
            validated: Dict[str, List[str]] = {}
            for name, words in stopword_presets.items():
                if isinstance(words, (str, bytes)):
                    raise ValueError(
                        f"stopword_presets[{name!r}] must be a list of strings, "
                        f"got {type(words).__name__}"
                    )
                if not isinstance(words, (list, tuple)):
                    raise ValueError(
                        f"stopword_presets[{name!r}] must be a list of strings, "
                        f"got {type(words).__name__}"
                    )
                if not all(isinstance(w, str) for w in words):
                    raise ValueError(f"stopword_presets[{name!r}] must contain only strings")
                validated[name] = list(words)
            payload["stopwordPresets"] = validated

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
        collection: str,
        property_name: str,
        text: str,
    ) -> executor.Result[TokenizeResult]:
        """Tokenize text using a property's configured tokenization settings.

        The server resolves the tokenization and analyzer configuration from
        the property's schema, so callers only supply the text.

        Args:
            collection: The collection that owns the property.
            property_name: The property name whose tokenization config to use.
            text: The text to tokenize.

        Returns:
            A TokenizeResult with indexed and query token lists.

        Raises:
            WeaviateUnsupportedFeatureError: If the server version is below 1.37.0.
        """
        self.__check_version()

        path = f"/schema/{_capitalize_first_letter(collection)}/properties/{property_name}/tokenize"
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
