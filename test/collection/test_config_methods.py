from typing import Any, Dict

from weaviate.collections.classes.config import VectorIndexType
from weaviate.collections.classes.config_methods import (
    _collection_config_from_json,
    _collection_config_simple_from_json,
    _collection_configs_simple_from_json,
    _nested_properties_from_config,
    _properties_from_config,
)

HNSW_CONFIG = {
    "skip": False,
    "cleanupIntervalSeconds": 300,
    "maxConnections": 64,
    "efConstruction": 128,
    "ef": -1,
    "dynamicEfMin": 100,
    "dynamicEfMax": 500,
    "dynamicEfFactor": 8,
    "vectorCacheMaxObjects": 1000000000000,
    "flatSearchCutoff": 40000,
    "distance": "cosine",
}


def _schema_with_vector_config(vector_config: Dict[str, Any]) -> Dict[str, Any]:
    """Build a minimal collection schema, as returned by Weaviate, around the given vectorConfig."""
    return {
        "class": "TestCollection",
        "vectorConfig": vector_config,
        "properties": [],
        "invertedIndexConfig": {
            "bm25": {"b": 0.75, "k1": 1.2},
            "cleanupIntervalSeconds": 60,
            "stopwords": {"preset": "en", "additions": None, "removals": None},
        },
        "multiTenancyConfig": {"enabled": False},
        "replicationConfig": {"factor": 1, "deletionStrategy": "NoAutomatedResolution"},
        "shardingConfig": {
            "virtualPerPhysical": 128,
            "desiredCount": 1,
            "actualCount": 1,
            "desiredVirtualCount": 128,
            "actualVirtualCount": 128,
            "key": "_id",
            "strategy": "hash",
            "function": "murmur3",
        },
    }


def test_collection_config_from_json_with_dropped_vector_index() -> None:
    """A vector whose index was dropped is returned without a vectorIndexConfig."""
    # Shape returned by Weaviate after `collection.config.delete_vector_index("dropped")`:
    # the entry stays in the schema, `vectorIndexType` becomes "none" and `vectorIndexConfig`
    # is omitted entirely.
    schema = _schema_with_vector_config(
        {
            "dropped": {"vectorizer": {"none": {}}, "vectorIndexType": "none"},
            "kept": {
                "vectorizer": {"none": {}},
                "vectorIndexType": "hnsw",
                "vectorIndexConfig": HNSW_CONFIG,
            },
        }
    )

    config = _collection_config_from_json(schema)

    assert config.vector_config is not None
    assert config.vector_config["dropped"].vector_index_config is None
    assert config.vector_config["kept"].vector_index_config is not None

    # The dropped vector must round-trip back to the "none" index type the server reported.
    as_dict = config.to_dict()
    assert as_dict["vectorConfig"]["dropped"]["vectorIndexType"] == VectorIndexType.NONE.value
    assert "vectorIndexConfig" not in as_dict["vectorConfig"]["dropped"]
    assert as_dict["vectorConfig"]["kept"]["vectorIndexType"] == VectorIndexType.HNSW.value


def test_collection_config_simple_from_json_with_dropped_vector_index() -> None:
    """`collections.list_all()` must not choke on a collection with a dropped vector index."""
    schema = _schema_with_vector_config(
        {"dropped": {"vectorizer": {"none": {}}, "vectorIndexType": "none"}}
    )

    config = _collection_config_simple_from_json(schema)

    assert config.vector_config is not None
    assert config.vector_config["dropped"].vector_index_config is None


def test_collection_config_simple_from_json_with_none_vectorizer_config() -> None:
    """Test that _collection_configs_simple_from_json handles None vectorizer config."""
    schema = {
        "classes": [
            {
                "class": "TestCollection",
                "vectorConfig": {
                    "default": {
                        "vectorizer": {"text2vec-transformers": None},
                        "vectorIndexType": "hnsw",
                        "vectorIndexConfig": {
                            "skip": False,
                            "cleanupIntervalSeconds": 300,
                            "maxConnections": 64,
                            "efConstruction": 128,
                            "ef": -1,
                            "dynamicEfMin": 100,
                            "dynamicEfMax": 500,
                            "dynamicEfFactor": 8,
                            "vectorCacheMaxObjects": 1000000000000,
                            "flatSearchCutoff": 40000,
                            "distance": "cosine",
                        },
                    }
                },
                "properties": [],
                "invertedIndexConfig": {
                    "bm25": {"b": 0.75, "k1": 1.2},
                    "cleanupIntervalSeconds": 60,
                    "stopwords": {"preset": "en", "additions": None, "removals": None},
                },
                "replicationConfig": {"factor": 1, "deletionStrategy": "NoAutomatedResolution"},
                "shardingConfig": {
                    "virtualPerPhysical": 128,
                    "desiredCount": 1,
                    "actualCount": 1,
                    "desiredVirtualCount": 128,
                    "actualVirtualCount": 128,
                    "key": "_id",
                    "strategy": "hash",
                    "function": "murmur3",
                },
                "vectorIndexType": "hnsw",
                "vectorIndexConfig": {
                    "skip": False,
                    "cleanupIntervalSeconds": 300,
                    "maxConnections": 64,
                    "efConstruction": 128,
                    "ef": -1,
                    "dynamicEfMin": 100,
                    "dynamicEfMax": 500,
                    "dynamicEfFactor": 8,
                    "vectorCacheMaxObjects": 1000000000000,
                    "flatSearchCutoff": 40000,
                    "distance": "cosine",
                },
            }
        ]
    }

    configs = _collection_configs_simple_from_json(schema)
    assert "TestCollection" in configs
    vec_config = configs["TestCollection"].vector_config
    assert vec_config is not None
    assert "default" in vec_config
    assert vec_config["default"].vectorizer.model == {}
    assert vec_config["default"].vectorizer.source_properties is None


def _make_text_prop(name: str, **extra) -> dict:
    base = {
        "name": name,
        "dataType": ["text"],
        "indexFilterable": True,
        "indexSearchable": True,
        "indexRangeFilters": False,
        "tokenization": "word",
    }
    base.update(extra)
    return base


def test_properties_from_config_parses_text_analyzer() -> None:
    schema = {
        "vectorizer": "none",
        "properties": [
            _make_text_prop(
                "title",
                textAnalyzer={"asciiFold": True, "asciiFoldIgnore": ["é"]},
            ),
            _make_text_prop("body"),
        ],
    }
    props = _properties_from_config(schema)
    title = next(p for p in props if p.name == "title")
    body = next(p for p in props if p.name == "body")

    assert title.text_analyzer is not None
    assert title.text_analyzer.ascii_fold is True
    assert title.text_analyzer.ascii_fold_ignore == ["é"]

    assert body.text_analyzer is None

    # The dataclass round-trips back to the wire format.
    assert title.to_dict()["textAnalyzer"] == {
        "asciiFold": True,
        "asciiFoldIgnore": ["é"],
    }
    assert "textAnalyzer" not in body.to_dict()


def test_properties_from_config_text_analyzer_omitted_when_no_ascii_fold() -> None:
    """If the server response omits asciiFold, the client treats text_analyzer as unset."""
    schema = {
        "vectorizer": "none",
        "properties": [
            # Server response with textAnalyzer present but no asciiFold key
            _make_text_prop("title", textAnalyzer={"asciiFoldIgnore": ["é"]}),
        ],
    }
    title = _properties_from_config(schema)[0]
    assert title.text_analyzer is None


def test_nested_properties_from_config_parses_text_analyzer() -> None:
    nested = _nested_properties_from_config(
        [
            _make_text_prop(
                "title",
                textAnalyzer={"asciiFold": True, "asciiFoldIgnore": ["ñ"]},
            ),
        ]
    )
    assert nested[0].text_analyzer is not None
    assert nested[0].text_analyzer.ascii_fold is True
    assert nested[0].text_analyzer.ascii_fold_ignore == ["ñ"]
    assert nested[0].to_dict()["textAnalyzer"] == {
        "asciiFold": True,
        "asciiFoldIgnore": ["ñ"],
    }


def test_properties_from_config_parses_stopword_preset_only() -> None:
    """A property with only stopwordPreset (no asciiFold) must still produce a text_analyzer."""
    schema = {
        "vectorizer": "none",
        "properties": [
            _make_text_prop("title", textAnalyzer={"stopwordPreset": "fr"}),
        ],
    }
    title = _properties_from_config(schema)[0]
    assert title.text_analyzer is not None
    assert title.text_analyzer.ascii_fold is False
    assert title.text_analyzer.ascii_fold_ignore is None
    assert title.text_analyzer.stopword_preset == "fr"


def test_properties_from_config_parses_combined_text_analyzer() -> None:
    schema = {
        "vectorizer": "none",
        "properties": [
            _make_text_prop(
                "title",
                textAnalyzer={
                    "asciiFold": True,
                    "asciiFoldIgnore": ["é"],
                    "stopwordPreset": "fr",
                },
            ),
        ],
    }
    title = _properties_from_config(schema)[0]
    assert title.text_analyzer is not None
    assert title.text_analyzer.ascii_fold is True
    assert title.text_analyzer.ascii_fold_ignore == ["é"]
    assert title.text_analyzer.stopword_preset == "fr"


def _full_schema(class_name: str, **inverted_overrides) -> dict:
    inverted = {
        "bm25": {"b": 0.75, "k1": 1.2},
        "cleanupIntervalSeconds": 60,
        "stopwords": {"preset": "en", "additions": None, "removals": None},
    }
    inverted.update(inverted_overrides)
    return {
        "class": class_name,
        "vectorizer": "none",
        "properties": [],
        "invertedIndexConfig": inverted,
        "replicationConfig": {"factor": 1, "deletionStrategy": "NoAutomatedResolution"},
        "shardingConfig": {
            "virtualPerPhysical": 128,
            "desiredCount": 1,
            "actualCount": 1,
            "desiredVirtualCount": 128,
            "actualVirtualCount": 128,
            "key": "_id",
            "strategy": "hash",
            "function": "murmur3",
        },
        "vectorIndexType": "hnsw",
        "vectorIndexConfig": {
            "skip": False,
            "cleanupIntervalSeconds": 300,
            "maxConnections": 64,
            "efConstruction": 128,
            "ef": -1,
            "dynamicEfMin": 100,
            "dynamicEfMax": 500,
            "dynamicEfFactor": 8,
            "vectorCacheMaxObjects": 1000000000000,
            "flatSearchCutoff": 40000,
            "distance": "cosine",
        },
    }


def test_collection_config_parses_stopword_presets() -> None:
    """The inverted index config exposes stopwordPresets when present in the schema."""
    schema = _full_schema(
        "TestStopwordPresets",
        stopwordPresets={
            "fr": ["le", "la", "les"],
            "es": ["el", "la", "los"],
        },
    )
    full = _collection_config_from_json(schema)
    assert full.inverted_index_config.stopword_presets == {
        "fr": ["le", "la", "les"],
        "es": ["el", "la", "los"],
    }


def test_collection_config_stopword_presets_absent() -> None:
    """If the server response omits stopwordPresets, the parsed value is None."""
    schema = _full_schema("TestNoStopwordPresets")
    full = _collection_config_from_json(schema)
    assert full.inverted_index_config.stopword_presets is None
