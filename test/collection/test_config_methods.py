
import pytest
from weaviate.collections.classes.config_methods import _collection_configs_simple_from_json

def test_collection_config_simple_from_json_with_none_vectorizer_config() -> None:
    """Test that _collection_configs_simple_from_json handles None vectorizer config."""
    schema = {
        "classes": [
            {
                "class": "TestCollection",
                "vectorConfig": {
                    "default": {
                        "vectorizer": {
                            "text2vec-transformers": None
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
                            "distance": "cosine"
                        }
                    }
                },
                "properties": [],
                "invertedIndexConfig": {
                        "bm25": {"b": 0.75, "k1": 1.2},
                        "cleanupIntervalSeconds": 60,
                        "stopwords": {"preset": "en", "additions": None, "removals": None}
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
                    "function": "murmur3"
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
                    "distance": "cosine"
                }
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
