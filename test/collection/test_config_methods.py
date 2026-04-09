from weaviate.collections.classes.config_methods import (
    _collection_configs_simple_from_json,
    _nested_properties_from_config,
    _properties_from_config,
)


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


def test_properties_from_config_text_analyzer_defaults_when_partial() -> None:
    schema = {
        "vectorizer": "none",
        "properties": [
            _make_text_prop("title", textAnalyzer={"asciiFoldIgnore": ["é"]}),
        ],
    }
    title = _properties_from_config(schema)[0]
    assert title.text_analyzer is not None
    # asciiFold defaults to False when omitted from the server response
    assert title.text_analyzer.ascii_fold is False
    assert title.text_analyzer.ascii_fold_ignore == ["é"]


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
