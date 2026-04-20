"""Integration tests for the tokenization module.

These tests cover the client's responsibilities:
- Correct serialization of inputs (enums, _TextAnalyzerConfigCreate, _StopwordsCreate)
- Correct deserialization of responses into the TokenizeResult object
- Client-side validation (_TextAnalyzerConfigCreate, stopwords/stopword_presets mutex)
- Version gate (>= 1.37.0)
- Both sync and async client paths

Server-side behavior this client relies on:
- Word tokenization defaults to preset "en" when no stopword config is sent.
- The generic /v1/tokenize response is minimal: only ``indexed`` and ``query``
  are returned. The property-level endpoint additionally returns ``tokenization``.
- ``stopwords`` and ``stopword_presets`` are mutually exclusive on the generic
  endpoint — the server rejects requests that set both.
"""

from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

import weaviate
from weaviate.collections.classes.config import (
    StopwordsPreset,
    Tokenization,
    _StopwordsCreate,
    _TextAnalyzerConfigCreate,
)
from weaviate.config import AdditionalConfig
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.tokenization.models import TokenizeResult


@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    c = weaviate.connect_to_local(
        additional_config=AdditionalConfig(timeout=(60, 120)),
    )
    yield c
    c.close()


@pytest.fixture(autouse=False)
def require_1_37(client: weaviate.WeaviateClient) -> None:
    if client._connection._weaviate_version.is_lower_than(1, 37, 0):
        pytest.skip("Tokenization requires Weaviate >= 1.37.0")


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[weaviate.WeaviateAsyncClient, None]:
    c = weaviate.use_async_with_local(
        additional_config=AdditionalConfig(timeout=(60, 120)),
    )
    await c.connect()
    yield c
    await c.close()


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("require_1_37")
class TestSerialization:
    """Verify the client correctly serializes different input forms."""

    @pytest.mark.parametrize(
        "tokenization,text,expected_indexed,expected_query",
        [
            # "the" is an English stopword — filtered from the query output
            # by the server's default "en" preset for word tokenization.
            (
                Tokenization.WORD,
                "The quick brown fox",
                ["the", "quick", "brown", "fox"],
                ["quick", "brown", "fox"],
            ),
            # Non-word tokenizations do not apply the default "en" preset.
            (
                Tokenization.LOWERCASE,
                "Hello World Test",
                ["hello", "world", "test"],
                ["hello", "world", "test"],
            ),
            (
                Tokenization.WHITESPACE,
                "Hello World Test",
                ["Hello", "World", "Test"],
                ["Hello", "World", "Test"],
            ),
            (Tokenization.FIELD, "  Hello World  ", ["Hello World"], ["Hello World"]),
            (Tokenization.TRIGRAM, "Hello", ["hel", "ell", "llo"], ["hel", "ell", "llo"]),
        ],
    )
    def test_tokenization_enum(
        self,
        client: weaviate.WeaviateClient,
        tokenization: Tokenization,
        text: str,
        expected_indexed: list,
        expected_query: list,
    ) -> None:
        result = client.tokenization.text(text=text, tokenization=tokenization)
        assert isinstance(result, TokenizeResult)
        assert result.indexed == expected_indexed
        assert result.query == expected_query
        # Generic endpoint does not echo tokenization back.
        assert result.tokenization is None

    def test_default_en_applied_for_word(self, client: weaviate.WeaviateClient) -> None:
        """Word tokenization defaults to the 'en' preset when no stopword
        config is supplied."""
        result = client.tokenization.text(
            text="The quick brown fox", tokenization=Tokenization.WORD
        )
        assert result.indexed == ["the", "quick", "brown", "fox"]
        # "the" removed by the server's default en preset.
        assert result.query == ["quick", "brown", "fox"]

    def test_opt_out_of_default_en(self, client: weaviate.WeaviateClient) -> None:
        """analyzerConfig.stopwordPreset='none' disables the default en."""
        cfg = _TextAnalyzerConfigCreate(stopword_preset=StopwordsPreset.NONE)
        result = client.tokenization.text(
            text="The quick brown fox",
            tokenization=Tokenization.WORD,
            analyzer_config=cfg,
        )
        assert result.query == ["the", "quick", "brown", "fox"]

    def test_ascii_fold(self, client: weaviate.WeaviateClient) -> None:
        cfg = _TextAnalyzerConfigCreate(ascii_fold=True)
        result = client.tokenization.text(
            text="L'école est fermée",
            tokenization=Tokenization.WORD,
            analyzer_config=cfg,
        )
        assert result.indexed == ["l", "ecole", "est", "fermee"]

    def test_ascii_fold_with_ignore(self, client: weaviate.WeaviateClient) -> None:
        cfg = _TextAnalyzerConfigCreate(ascii_fold=True, ascii_fold_ignore=["é"])
        result = client.tokenization.text(
            text="L'école est fermée",
            tokenization=Tokenization.WORD,
            analyzer_config=cfg,
        )
        assert result.indexed == ["l", "école", "est", "fermée"]

    def test_stopword_preset_enum(self, client: weaviate.WeaviateClient) -> None:
        cfg = _TextAnalyzerConfigCreate(stopword_preset=StopwordsPreset.EN)
        result = client.tokenization.text(
            text="The quick brown fox",
            tokenization=Tokenization.WORD,
            analyzer_config=cfg,
        )
        assert "the" not in result.query
        assert "quick" in result.query

    def test_stopword_preset_string(self, client: weaviate.WeaviateClient) -> None:
        cfg = _TextAnalyzerConfigCreate(stopword_preset="en")
        result = client.tokenization.text(
            text="The quick brown fox",
            tokenization=Tokenization.WORD,
            analyzer_config=cfg,
        )
        assert "the" not in result.query

    def test_ascii_fold_combined_with_stopwords(self, client: weaviate.WeaviateClient) -> None:
        cfg = _TextAnalyzerConfigCreate(
            ascii_fold=True, ascii_fold_ignore=["é"], stopword_preset=StopwordsPreset.EN
        )
        result = client.tokenization.text(
            text="The école est fermée",
            tokenization=Tokenization.WORD,
            analyzer_config=cfg,
        )
        assert result.indexed == ["the", "école", "est", "fermée"]
        assert "the" not in result.query
        assert "école" in result.query

    def test_stopwords_fallback(self, client: weaviate.WeaviateClient) -> None:
        """Top-level stopwords acts as the fallback detector when no
        analyzerConfig.stopwordPreset is set."""
        sw = _StopwordsCreate(
            preset=StopwordsPreset.EN, additions=["quick"], removals=None
        )
        result = client.tokenization.text(
            text="the quick brown fox",
            tokenization=Tokenization.WORD,
            stopwords=sw,
        )
        assert result.indexed == ["the", "quick", "brown", "fox"]
        # "the" (en) and "quick" (addition) filtered.
        assert result.query == ["brown", "fox"]

    def test_stopwords_additions_default_preset_to_en(
        self, client: weaviate.WeaviateClient
    ) -> None:
        """Caller omits preset, passes only additions. Server defaults preset
        to 'en' and builds detector from en + additions."""
        sw = _StopwordsCreate(preset=None, additions=["hello"], removals=None)
        result = client.tokenization.text(
            text="the quick hello world",
            tokenization=Tokenization.WORD,
            stopwords=sw,
        )
        assert result.query == ["quick", "world"]

    def test_stopwords_removals_default_preset_to_en(
        self, client: weaviate.WeaviateClient
    ) -> None:
        """Caller omits preset, passes only removals. 'the' is removed from
        the en list so it passes through."""
        sw = _StopwordsCreate(preset=None, additions=None, removals=["the"])
        result = client.tokenization.text(
            text="the quick is fast",
            tokenization=Tokenization.WORD,
            stopwords=sw,
        )
        # "is" still in en, "the" removed.
        assert result.query == ["the", "quick", "fast"]

    def test_stopword_presets_named_reference(self, client: weaviate.WeaviateClient) -> None:
        """Define a named preset via stopword_presets, select it via
        analyzerConfig.stopwordPreset. Word lists use the collection shape."""
        result = client.tokenization.text(
            text="hello world test",
            tokenization=Tokenization.WORD,
            analyzer_config=_TextAnalyzerConfigCreate(stopword_preset="custom"),
            stopword_presets={"custom": ["test"]},
        )
        assert result.indexed == ["hello", "world", "test"]
        assert result.query == ["hello", "world"]

    def test_stopword_presets_override_builtin_en(
        self, client: weaviate.WeaviateClient
    ) -> None:
        """A user-defined preset sharing a name with a built-in replaces the
        built-in entirely, including on the default-en path for word
        tokenization."""
        result = client.tokenization.text(
            text="the quick hello world",
            tokenization=Tokenization.WORD,
            stopword_presets={"en": ["hello"]},
        )
        assert result.indexed == ["the", "quick", "hello", "world"]
        # "the" no longer filtered (built-in en replaced), "hello" is.
        assert result.query == ["the", "quick", "world"]


# ---------------------------------------------------------------------------
# Deserialization
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("require_1_37")
class TestDeserialization:
    """Verify the client correctly deserializes response fields into
    TokenizeResult."""

    def test_generic_result_shape(self, client: weaviate.WeaviateClient) -> None:
        """Generic endpoint returns only indexed and query; tokenization is
        not echoed back."""
        result = client.tokenization.text(text="hello", tokenization=Tokenization.WORD)
        assert isinstance(result, TokenizeResult)
        assert isinstance(result.indexed, list)
        assert isinstance(result.query, list)
        assert result.tokenization is None

    def test_property_result_populates_tokenization(
        self, client: weaviate.WeaviateClient
    ) -> None:
        """Property endpoint returns tokenization — the server resolved it
        from the property's schema rather than the caller sending it."""
        client.collections.delete("TestDeserPropTypes")
        try:
            client.collections.create_from_dict(
                {
                    "class": "TestDeserPropTypes",
                    "vectorizer": "none",
                    "properties": [
                        {
                            "name": "tag",
                            "dataType": ["text"],
                            "tokenization": "field",
                        },
                    ],
                }
            )
            col = client.collections.get("TestDeserPropTypes")
            result = col.config.tokenize_property(property_name="tag", text="  Hello World  ")
            assert isinstance(result, TokenizeResult)
            assert result.tokenization == Tokenization.FIELD
            assert result.indexed == ["Hello World"]
        finally:
            client.collections.delete("TestDeserPropTypes")


# ---------------------------------------------------------------------------
# Client-side validation
# ---------------------------------------------------------------------------


class TestClientSideValidation:
    """Verify that client-side validation rejects invalid input before
    hitting the server."""

    def test_ascii_fold_ignore_without_fold_raises(self) -> None:
        with pytest.raises(ValueError, match="asciiFoldIgnore"):
            _TextAnalyzerConfigCreate(ascii_fold=False, ascii_fold_ignore=["é"])

    def test_ascii_fold_ignore_without_fold_default_raises(self) -> None:
        with pytest.raises(ValueError, match="asciiFoldIgnore"):
            _TextAnalyzerConfigCreate(ascii_fold_ignore=["é"])

    def test_valid_config_does_not_raise(self) -> None:
        cfg = _TextAnalyzerConfigCreate(ascii_fold=True, ascii_fold_ignore=["é", "ñ"])
        assert cfg.asciiFold is True
        assert cfg.asciiFoldIgnore == ["é", "ñ"]

    def test_fold_without_ignore_is_valid(self) -> None:
        cfg = _TextAnalyzerConfigCreate(ascii_fold=True)
        assert cfg.asciiFold is True
        assert cfg.asciiFoldIgnore is None

    def test_stopword_preset_only_is_valid(self) -> None:
        cfg = _TextAnalyzerConfigCreate(stopword_preset="en")
        assert cfg.stopwordPreset == "en"

    def test_empty_config_is_valid(self) -> None:
        cfg = _TextAnalyzerConfigCreate()
        assert cfg.asciiFold is None
        assert cfg.asciiFoldIgnore is None
        assert cfg.stopwordPreset is None

    def test_stopwords_and_stopword_presets_mutex(
        self, client: weaviate.WeaviateClient
    ) -> None:
        """Client rejects the mutex violation locally with ValueError, before
        sending the request (which the server would also reject with 422)."""
        if client._connection._weaviate_version.is_lower_than(1, 37, 0):
            pytest.skip("Tokenization requires Weaviate >= 1.37.0")
        with pytest.raises(ValueError, match="mutually exclusive"):
            client.tokenization.text(
                text="hello",
                tokenization=Tokenization.WORD,
                stopwords=_StopwordsCreate(
                    preset=StopwordsPreset.EN, additions=None, removals=None
                ),
                stopword_presets={"custom": ["hello"]},
            )


# ---------------------------------------------------------------------------
# Version gate
# ---------------------------------------------------------------------------


class TestVersionGate:
    """On Weaviate < 1.37 the client must raise before sending the request."""

    def test_text_raises_on_old_server(self, client: weaviate.WeaviateClient) -> None:
        if client._connection._weaviate_version.is_at_least(1, 37, 0):
            pytest.skip("Version gate only applies to Weaviate < 1.37.0")
        with pytest.raises(WeaviateUnsupportedFeatureError):
            client.tokenization.text(text="hello", tokenization=Tokenization.WORD)

    def test_tokenize_property_raises_on_old_server(self, client: weaviate.WeaviateClient) -> None:
        if client._connection._weaviate_version.is_at_least(1, 37, 0):
            pytest.skip("Version gate only applies to Weaviate < 1.37.0")
        col = client.collections.get("Any")
        with pytest.raises(WeaviateUnsupportedFeatureError):
            col.config.tokenize_property(property_name="title", text="hello")


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("require_1_37")
class TestAsyncClient:
    """Verify text() and tokenize_property() work through the async client."""

    @pytest.mark.asyncio
    async def test_text_tokenize(self, async_client: weaviate.WeaviateAsyncClient) -> None:
        result = await async_client.tokenization.text(
            text="The quick brown fox",
            tokenization=Tokenization.WORD,
        )
        assert isinstance(result, TokenizeResult)
        assert result.indexed == ["the", "quick", "brown", "fox"]
        # default "en" applied server-side.
        assert result.query == ["quick", "brown", "fox"]

    @pytest.mark.asyncio
    async def test_text_with_stopwords_fallback(
        self, async_client: weaviate.WeaviateAsyncClient
    ) -> None:
        sw = _StopwordsCreate(preset=StopwordsPreset.EN, additions=["quick"], removals=None)
        result = await async_client.tokenization.text(
            text="the quick brown fox",
            tokenization=Tokenization.WORD,
            stopwords=sw,
        )
        assert result.indexed == ["the", "quick", "brown", "fox"]
        assert result.query == ["brown", "fox"]

    @pytest.mark.asyncio
    async def test_property_tokenize(self, async_client: weaviate.WeaviateAsyncClient) -> None:
        await async_client.collections.delete("TestAsyncPropTokenize")
        try:
            await async_client.collections.create_from_dict(
                {
                    "class": "TestAsyncPropTokenize",
                    "vectorizer": "none",
                    "properties": [
                        {
                            "name": "title",
                            "dataType": ["text"],
                            "tokenization": "word",
                            "textAnalyzer": {"stopwordPreset": "en"},
                        },
                    ],
                }
            )
            col = async_client.collections.get("TestAsyncPropTokenize")
            result = await col.config.tokenize_property(
                property_name="title",
                text="The quick brown fox",
            )
            assert isinstance(result, TokenizeResult)
            assert result.tokenization == Tokenization.WORD
            assert result.indexed == ["the", "quick", "brown", "fox"]
            assert "the" not in result.query
            assert "quick" in result.query
        finally:
            await async_client.collections.delete("TestAsyncPropTokenize")
