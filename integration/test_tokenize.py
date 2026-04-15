"""Integration tests for the tokenize module.

These tests cover the client's responsibilities:
- Correct serialization of inputs (enums, _TextAnalyzerConfigCreate, kwargs)
- Correct deserialization of responses into typed objects
- Client-side validation (_TextAnalyzerConfigCreate rejects invalid input)
- Both sync and async client paths
"""

from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

import weaviate
from weaviate.collections.classes.config import (
    StopwordsConfig,
    StopwordsPreset,
    TextAnalyzerConfig,
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


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[weaviate.WeaviateAsyncClient, None]:
    c = weaviate.use_async_with_local(
        additional_config=AdditionalConfig(timeout=(60, 120)),
    )
    await c.connect()
    yield c
    await c.close()


# ---------------------------------------------------------------------------
# Serialization: enums, strings, kwargs, _TextAnalyzerConfigCreate
# ---------------------------------------------------------------------------


class TestSerialization:
    """Verify the client correctly serializes different input forms."""

    @pytest.mark.parametrize(
        "tokenization,text,expected_tokens",
        [
            (Tokenization.WORD, "The quick brown fox", ["the", "quick", "brown", "fox"]),
            (Tokenization.LOWERCASE, "Hello World Test", ["hello", "world", "test"]),
            (Tokenization.WHITESPACE, "Hello World Test", ["Hello", "World", "Test"]),
            (Tokenization.FIELD, "  Hello World  ", ["Hello World"]),
            (Tokenization.TRIGRAM, "Hello", ["hel", "ell", "llo"]),
        ],
    )
    def test_tokenization_enum(
        self,
        client: weaviate.WeaviateClient,
        tokenization: Tokenization,
        text: str,
        expected_tokens: list,
    ) -> None:
        result = client.tokenization.text(text=text, tokenization=tokenization)
        assert isinstance(result, TokenizeResult)
        assert result.tokenization == tokenization.value
        assert result.indexed == expected_tokens
        assert result.query == expected_tokens

    def test_tokenization_string(self, client: weaviate.WeaviateClient) -> None:
        result = client.tokenization.text(text="hello world", tokenization="word")
        assert result.tokenization == "word"
        assert result.indexed == ["hello", "world"]

    def test_stopword_preset_enum(self, client: weaviate.WeaviateClient) -> None:
        result = client.tokenization.text(
            text="The quick brown fox",
            tokenization=Tokenization.WORD,
            stopword_preset=StopwordsPreset.EN,
        )
        assert "the" not in result.query
        assert "quick" in result.query

    def test_stopword_preset_string(self, client: weaviate.WeaviateClient) -> None:
        result = client.tokenization.text(
            text="The quick brown fox",
            tokenization=Tokenization.WORD,
            stopword_preset="en",
        )
        assert "the" not in result.query

    def test_ascii_fold_via_kwargs(self, client: weaviate.WeaviateClient) -> None:
        result = client.tokenization.text(
            text="L'école est fermée",
            tokenization=Tokenization.WORD,
            ascii_fold=True,
        )
        assert result.indexed == ["l", "ecole", "est", "fermee"]

    def test_ascii_fold_via_analyzer_config(self, client: weaviate.WeaviateClient) -> None:
        cfg = _TextAnalyzerConfigCreate(ascii_fold=True)
        result = client.tokenization.text(
            text="L'école est fermée",
            tokenization=Tokenization.WORD,
            analyzer_config=cfg,
        )
        assert result.indexed == ["l", "ecole", "est", "fermee"]

    def test_analyzer_config_and_kwargs_produce_same_result(
        self, client: weaviate.WeaviateClient
    ) -> None:
        """analyzer_config object and equivalent kwargs must produce identical output."""
        cfg = _TextAnalyzerConfigCreate(
            ascii_fold=True, ascii_fold_ignore=["é"], stopword_preset=StopwordsPreset.EN
        )
        via_config = client.tokenization.text(
            text="L'école est fermée",
            tokenization=Tokenization.WORD,
            analyzer_config=cfg,
        )
        via_kwargs = client.tokenization.text(
            text="L'école est fermée",
            tokenization=Tokenization.WORD,
            ascii_fold=True,
            ascii_fold_ignore=["é"],
            stopword_preset=StopwordsPreset.EN,
        )
        assert via_config.indexed == via_kwargs.indexed
        assert via_config.query == via_kwargs.query

    def test_stopword_presets_serialization(self, client: weaviate.WeaviateClient) -> None:
        result = client.tokenization.text(
            text="hello world test",
            tokenization=Tokenization.WORD,
            stopword_preset="custom",
            stopword_presets={
                "custom": _StopwordsCreate(preset=None, additions=["test"], removals=None),
            },
        )
        assert result.indexed == ["hello", "world", "test"]
        assert result.query == ["hello", "world"]

    def test_stopword_presets_with_base_and_removals(self, client: weaviate.WeaviateClient) -> None:
        result = client.tokenization.text(
            text="the quick",
            tokenization=Tokenization.WORD,
            stopword_preset="en-no-the",
            stopword_presets={
                "en-no-the": _StopwordsCreate(
                    preset=StopwordsPreset.EN, additions=None, removals=["the"]
                ),
            },
        )
        assert result.indexed == ["the", "quick"]
        assert result.query == ["the", "quick"]


# ---------------------------------------------------------------------------
# Deserialization: typed response fields
# ---------------------------------------------------------------------------


class TestDeserialization:
    """Verify the client correctly deserializes response fields into typed objects."""

    def test_result_type(self, client: weaviate.WeaviateClient) -> None:
        result = client.tokenization.text(text="hello", tokenization=Tokenization.WORD)
        assert isinstance(result, TokenizeResult)
        assert isinstance(result.indexed, list)
        assert isinstance(result.query, list)

    def test_analyzer_config_deserialized(self, client: weaviate.WeaviateClient) -> None:
        result = client.tokenization.text(
            text="L'école",
            tokenization=Tokenization.WORD,
            ascii_fold=True,
            ascii_fold_ignore=["é"],
            stopword_preset=StopwordsPreset.EN,
        )
        assert isinstance(result.analyzer_config, TextAnalyzerConfig)
        assert result.analyzer_config.ascii_fold is True
        assert result.analyzer_config.ascii_fold_ignore == ["é"]
        assert result.analyzer_config.stopword_preset == "en"

    def test_no_analyzer_config_returns_none(self, client: weaviate.WeaviateClient) -> None:
        result = client.tokenization.text(text="hello", tokenization=Tokenization.WORD)
        assert result.analyzer_config is None

    def test_stopword_config_deserialized_on_property(
        self, client: weaviate.WeaviateClient
    ) -> None:
        """Property endpoint returns stopwordConfig; verify it deserializes to StopwordsConfig."""
        client.collections.delete("TestDeserStopword")
        try:
            client.collections.create_from_dict(
                {
                    "class": "TestDeserStopword",
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
            result = client.tokenization.for_property(
                collection_name="TestDeserStopword",
                property_name="title",
                text="the quick",
            )
            assert isinstance(result, TokenizeResult)
            assert result.tokenization == "word"
            # Stopword config should be deserialized when present
            if result.stopword_config is not None:
                assert isinstance(result.stopword_config, StopwordsConfig)
        finally:
            client.collections.delete("TestDeserStopword")

    def test_property_result_types(self, client: weaviate.WeaviateClient) -> None:
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
            result = client.tokenization.for_property(
                collection_name="TestDeserPropTypes",
                property_name="tag",
                text="  Hello World  ",
            )
            assert isinstance(result, TokenizeResult)
            assert result.tokenization == "field"
            assert result.indexed == ["Hello World"]
        finally:
            client.collections.delete("TestDeserPropTypes")


# ---------------------------------------------------------------------------
# Client-side validation (_TextAnalyzerConfigCreate)
# ---------------------------------------------------------------------------


class TestClientSideValidation:
    """Verify that _TextAnalyzerConfigCreate rejects invalid input before hitting the server."""

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

    def test_for_property_raises_on_old_server(self, client: weaviate.WeaviateClient) -> None:
        if client._connection._weaviate_version.is_at_least(1, 37, 0):
            pytest.skip("Version gate only applies to Weaviate < 1.37.0")
        with pytest.raises(WeaviateUnsupportedFeatureError):
            client.tokenization.for_property(
                collection_name="Any", property_name="title", text="hello"
            )


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------


class TestAsyncClient:
    """Verify both text() and property() work through the async client."""

    @pytest.mark.asyncio
    async def test_text_tokenize(self, async_client: weaviate.WeaviateAsyncClient) -> None:
        result = await async_client.tokenization.text(
            text="The quick brown fox",
            tokenization=Tokenization.WORD,
        )
        assert isinstance(result, TokenizeResult)
        assert result.indexed == ["the", "quick", "brown", "fox"]

    @pytest.mark.asyncio
    async def test_text_with_analyzer_config(
        self, async_client: weaviate.WeaviateAsyncClient
    ) -> None:
        cfg = _TextAnalyzerConfigCreate(ascii_fold=True, stopword_preset=StopwordsPreset.EN)
        result = await async_client.tokenization.text(
            text="L'école est fermée",
            tokenization=Tokenization.WORD,
            analyzer_config=cfg,
        )
        assert result.indexed == ["l", "ecole", "est", "fermee"]
        assert isinstance(result.analyzer_config, TextAnalyzerConfig)
        assert result.analyzer_config.ascii_fold is True

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
            result = await async_client.tokenization.for_property(
                collection_name="TestAsyncPropTokenize",
                property_name="title",
                text="The quick brown fox",
            )
            assert isinstance(result, TokenizeResult)
            assert result.tokenization == "word"
            assert result.indexed == ["the", "quick", "brown", "fox"]
            assert "the" not in result.query
            assert "quick" in result.query
        finally:
            await async_client.collections.delete("TestAsyncPropTokenize")
