from typing import Literal, Optional


def multi_vector_schema(quantizer: Optional[Literal["pq", "bq", "sq"]] = None) -> dict:
    return {
        "class": "Something",
        "invertedIndexConfig": {
            "bm25": {"b": 0.75, "k1": 1.2},
            "cleanupIntervalSeconds": 60,
            "stopwords": {"additions": None, "preset": "en", "removals": None},
        },
        "multiTenancyConfig": {
            "autoTenantActivation": False,
            "autoTenantCreation": False,
            "enabled": False,
        },
        "properties": [
            {
                "dataType": ["text"],
                "indexFilterable": True,
                "indexRangeFilters": False,
                "indexSearchable": True,
                "name": "name",
                "tokenization": "word",
            }
        ],
        "replicationConfig": {"asyncEnabled": False, "factor": 1},
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
        "vectorConfig": {
            "boi": {
                "vectorIndexConfig": {
                    "skip": False,
                    "cleanupIntervalSeconds": 300,
                    "maxConnections": 32,
                    "efConstruction": 128,
                    "ef": -1,
                    "dynamicEfMin": 100,
                    "dynamicEfMax": 500,
                    "dynamicEfFactor": 8,
                    "vectorCacheMaxObjects": 1000000000000,
                    "flatSearchCutoff": 40000,
                    "distance": "cosine",
                    "pq": {
                        "enabled": quantizer == "pq",
                        "bitCompression": False,
                        "segments": 0,
                        "centroids": 256,
                        "trainingLimit": 100000,
                        "encoder": {"type": "kmeans", "distribution": "log-normal"},
                    },
                    "bq": {"enabled": quantizer == "bq"},
                    "sq": {
                        "enabled": quantizer == "sq",
                        "trainingLimit": 100000,
                        "rescoreLimit": 20,
                    },
                },
                "vectorIndexType": "hnsw",
                "vectorizer": {"none": {}},
            },
            "yeh": {
                "vectorIndexConfig": {
                    "skip": False,
                    "cleanupIntervalSeconds": 300,
                    "maxConnections": 32,
                    "efConstruction": 128,
                    "ef": -1,
                    "dynamicEfMin": 100,
                    "dynamicEfMax": 500,
                    "dynamicEfFactor": 8,
                    "vectorCacheMaxObjects": 1000000000000,
                    "flatSearchCutoff": 40000,
                    "distance": "cosine",
                    "pq": {
                        "enabled": quantizer == "pq",
                        "bitCompression": False,
                        "segments": 0,
                        "centroids": 256,
                        "trainingLimit": 100000,
                        "encoder": {"type": "kmeans", "distribution": "log-normal"},
                    },
                    "bq": {"enabled": quantizer == "bq"},
                    "sq": {
                        "enabled": quantizer == "sq",
                        "trainingLimit": 100000,
                        "rescoreLimit": 20,
                    },
                },
                "vectorIndexType": "hnsw",
                "vectorizer": {"none": {}},
            },
        },
    }
