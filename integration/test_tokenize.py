"""Integration tests for the tokenization module.

These tests cover the client's responsibilities:
- Correct serialization of inputs (enums, TextAnalyzerConfigCreate, StopwordsCreate)
- Correct deserialization of responses into the TokenizeResult object
- Client-side validation (TextAnalyzerConfigCreate, stopwords/stopword_presets mutex)
- Version gate (>= 1.37.0)
- Both sync and async client paths

Server-side behavior this client relies on:
- Word tokenization defaults to preset "en" when no stopword config is sent.
- Both endpoints return only ``indexed`` and ``query``.
- ``stopwords`` and ``stopword_presets`` are mutually exclusive on the generic
  endpoint — the server rejects requests that set both.
"""

from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

import weaviate
from weaviate.classes.tokenization import (
    StopwordsCreate,
    StopwordsPreset,
    TextAnalyzerConfigCreate,
    Tokenization,
    TokenizeResult,
)
from weaviate.config import AdditionalConfig
from weaviate.exceptions import WeaviateUnsupportedFeatureError


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


@pytest.fixture
def recipe_collection(client: weaviate.WeaviateClient) -> Generator:
    """Collection with a `recipe` word-tokenized property and an en + ["quick"] stopwords config."""
    name = "TestTokenizeRecipe"
    client.collections.delete(name)
    client.collections.create_from_dict(
        {
            "class": name,
            "vectorizer": "none",
            "invertedIndexConfig": {
                "stopwords": {"preset": "en", "additions": ["quick"]},
            },
            "properties": [
                {"name": "recipe", "dataType": ["text"], "tokenization": "word"},
            ],
        }
    )
    try:
        yield client.collections.get(name)
    finally:
        client.collections.delete(name)


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

    @pytest.mark.parametrize(
        "call_kwargs,expected_indexed,expected_query",
        [
            (
                {"text": "The quick brown fox"},
                ["the", "quick", "brown", "fox"],
                ["quick", "brown", "fox"],
            ),
            (
                {
                    "text": "The quick brown fox",
                    "analyzer_config": TextAnalyzerConfigCreate(
                        stopword_preset=StopwordsPreset.NONE
                    ),
                },
                ["the", "quick", "brown", "fox"],
                ["the", "quick", "brown", "fox"],
            ),
            (
                {
                    "text": "L'école est fermée",
                    "analyzer_config": TextAnalyzerConfigCreate(ascii_fold=True),
                },
                ["l", "ecole", "est", "fermee"],
                ["l", "ecole", "est", "fermee"],
            ),
            (
                {
                    "text": "L'école est fermée",
                    "analyzer_config": TextAnalyzerConfigCreate(
                        ascii_fold=True, ascii_fold_ignore=["é"]
                    ),
                },
                ["l", "école", "est", "fermée"],
                ["l", "école", "est", "fermée"],
            ),
            (
                {
                    "text": "The quick brown fox",
                    "analyzer_config": TextAnalyzerConfigCreate(stopword_preset=StopwordsPreset.EN),
                },
                ["the", "quick", "brown", "fox"],
                ["quick", "brown", "fox"],
            ),
            (
                {
                    "text": "The quick brown fox",
                    "analyzer_config": TextAnalyzerConfigCreate(stopword_preset="en"),
                },
                ["the", "quick", "brown", "fox"],
                ["quick", "brown", "fox"],
            ),
            (
                {
                    "text": "The école est fermée",
                    "analyzer_config": TextAnalyzerConfigCreate(
                        ascii_fold=True,
                        ascii_fold_ignore=["é"],
                        stopword_preset=StopwordsPreset.EN,
                    ),
                },
                ["the", "école", "est", "fermée"],
                ["école", "est", "fermée"],
            ),
            (
                {
                    "text": "the quick brown fox",
                    "stopwords": StopwordsCreate(
                        preset=StopwordsPreset.EN, additions=["quick"], removals=None
                    ),
                },
                ["the", "quick", "brown", "fox"],
                ["brown", "fox"],
            ),
            (
                {
                    "text": "the quick hello world",
                    "stopwords": StopwordsCreate(preset=None, additions=["hello"], removals=None),
                },
                ["the", "quick", "hello", "world"],
                ["quick", "world"],
            ),
            (
                {
                    "text": "the quick is fast",
                    "stopwords": StopwordsCreate(preset=None, additions=None, removals=["the"]),
                },
                ["the", "quick", "is", "fast"],
                ["the", "quick", "fast"],
            ),
            (
                {
                    "text": "hello world test",
                    "analyzer_config": TextAnalyzerConfigCreate(stopword_preset="custom"),
                    "stopword_presets": {"custom": ["test"]},
                },
                ["hello", "world", "test"],
                ["hello", "world"],
            ),
            (
                {
                    "text": "the quick hello world",
                    "stopword_presets": {"en": ["hello"]},
                },
                ["the", "quick", "hello", "world"],
                ["the", "quick", "world"],
            ),
        ],
        ids=[
            "default_en_applied_for_word",
            "opt_out_of_default_en",
            "ascii_fold",
            "ascii_fold_with_ignore",
            "stopword_preset_enum",
            "stopword_preset_string",
            "ascii_fold_combined_with_stopwords",
            "stopwords_fallback",
            "stopwords_additions_default_preset_to_en",
            "stopwords_removals_default_preset_to_en",
            "stopword_presets_named_reference",
            "stopword_presets_override_builtin_en",
        ],
    )
    def test_text_tokenize(
        self,
        client: weaviate.WeaviateClient,
        call_kwargs: dict,
        expected_indexed: list,
        expected_query: list,
    ) -> None:
        result = client.tokenization.text(tokenization=Tokenization.WORD, **call_kwargs)
        assert isinstance(result, TokenizeResult)
        assert result.indexed == expected_indexed
        assert result.query == expected_query

    def test_text_from_collection_config(
        self, client: weaviate.WeaviateClient, recipe_collection
    ) -> None:
        """Values round-tripped through config.get() feed back into tokenization.text()."""
        config = recipe_collection.config.get()
        recipe = next(p for p in config.properties if p.name == "recipe")
        stopwords = config.inverted_index_config.stopwords
        result = client.tokenization.text(
            text="the quick brown fox",
            tokenization=recipe.tokenization,
            stopwords=stopwords,
        )
        assert result.indexed == ["the", "quick", "brown", "fox"]
        assert result.query == ["brown", "fox"]

    def test_property_and_generic_endpoints_agree(
        self, client: weaviate.WeaviateClient, recipe_collection
    ) -> None:
        """Property endpoint (server resolves config from schema) produces the same indexed/query as the generic endpoint fed the same config."""
        config = recipe_collection.config.get()
        recipe = next(p for p in config.properties if p.name == "recipe")
        stopwords = config.inverted_index_config.stopwords

        text = "the quick brown fox"
        via_property = client.tokenization.for_property(
            collection=recipe_collection.name, property_name="recipe", text=text
        )
        via_generic = client.tokenization.text(
            text=text,
            tokenization=recipe.tokenization,
            stopwords=stopwords,
        )

        assert via_property.indexed == via_generic.indexed
        assert via_property.query == via_generic.query


# ---------------------------------------------------------------------------
# Deserialization
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("require_1_37")
class TestDeserialization:
    """Verify the client correctly deserializes response fields into TokenizeResult."""

    def test_property_result_shape(self, client: weaviate.WeaviateClient) -> None:
        """Property endpoint response deserializes into TokenizeResult — server resolves tokenization from the property's schema."""
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
                collection="TestDeserPropTypes", property_name="tag", text="  Hello World  "
            )
            assert isinstance(result, TokenizeResult)
            assert result.indexed == ["Hello World"]
        finally:
            client.collections.delete("TestDeserPropTypes")


# ---------------------------------------------------------------------------
# Client-side validation
# ---------------------------------------------------------------------------


class TestClientSideValidation:
    """Verify that client-side validation rejects invalid input before hitting the server."""

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"ascii_fold": False, "ascii_fold_ignore": ["é"]},
            {"ascii_fold_ignore": ["é"]},
        ],
        ids=["explicit_false", "default"],
    )
    def test_ascii_fold_ignore_without_fold_raises(self, kwargs: dict) -> None:
        with pytest.raises(ValueError, match="asciiFoldIgnore"):
            TextAnalyzerConfigCreate(**kwargs)

    @pytest.mark.parametrize(
        "kwargs,expected",
        [
            (
                {"ascii_fold": True, "ascii_fold_ignore": ["é", "ñ"]},
                {"asciiFold": True, "asciiFoldIgnore": ["é", "ñ"]},
            ),
            (
                {"ascii_fold": True},
                {"asciiFold": True, "asciiFoldIgnore": None},
            ),
            (
                {"stopword_preset": "en"},
                {"stopwordPreset": "en"},
            ),
            (
                {},
                {"asciiFold": None, "asciiFoldIgnore": None, "stopwordPreset": None},
            ),
        ],
        ids=["fold_with_ignore", "fold_without_ignore", "stopword_preset_only", "empty"],
    )
    def test_valid_config(self, kwargs: dict, expected: dict) -> None:
        cfg = TextAnalyzerConfigCreate(**kwargs)
        for attr, value in expected.items():
            assert getattr(cfg, attr) == value

    def test_stopwords_and_stopword_presets_mutex(self, client: weaviate.WeaviateClient) -> None:
        """Client rejects the mutex violation locally with ValueError, before sending the request (which the server would also reject with 422)."""
        if client._connection._weaviate_version.is_lower_than(1, 37, 0):
            pytest.skip("Tokenization requires Weaviate >= 1.37.0")
        with pytest.raises(ValueError, match="mutually exclusive"):
            client.tokenization.text(
                text="hello",
                tokenization=Tokenization.WORD,
                stopwords=StopwordsCreate(preset=StopwordsPreset.EN, additions=None, removals=None),
                stopword_presets={"custom": ["hello"]},
            )

    @pytest.mark.parametrize(
        "stopword_presets,match",
        [
            ({"custom": "hello"}, "must be a list of strings"),
            (
                {
                    "custom": StopwordsCreate(
                        preset=StopwordsPreset.EN, additions=None, removals=None
                    ),
                },
                "must be a list of strings",
            ),
            ({"custom": ["hello", 123]}, "must contain only strings"),
        ],
        ids=["str_value", "pydantic_model_value", "non_string_element"],
    )
    def test_stopword_presets_invalid_shape_raises(
        self,
        client: weaviate.WeaviateClient,
        stopword_presets: dict,
        match: str,
    ) -> None:
        """Client rejects malformed stopword_presets values locally before sending — str would silently split into characters; a pydantic model would serialize to field tuples."""
        if client._connection._weaviate_version.is_lower_than(1, 37, 0):
            pytest.skip("Tokenization requires Weaviate >= 1.37.0")
        with pytest.raises(ValueError, match=match):
            client.tokenization.text(
                text="hello",
                tokenization=Tokenization.WORD,
                stopword_presets=stopword_presets,
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
        with pytest.raises(WeaviateUnsupportedFeatureError):
            client.tokenization.for_property(collection="Any", property_name="title", text="hello")


# ---------------------------------------------------------------------------
# Async client
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("require_1_37")
class TestAsyncClient:
    """Verify tokenization.text() and tokenization.for_property() work through the async client."""

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
        sw = StopwordsCreate(preset=StopwordsPreset.EN, additions=["quick"], removals=None)
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
            result = await async_client.tokenization.for_property(
                collection="TestAsyncPropTokenize",
                property_name="title",
                text="The quick brown fox",
            )
            assert isinstance(result, TokenizeResult)
            assert result.indexed == ["the", "quick", "brown", "fox"]
            assert result.query == ["quick", "brown", "fox"]
        finally:
            await async_client.collections.delete("TestAsyncPropTokenize")
