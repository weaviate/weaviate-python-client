mock_class = {
    "class": "Something",
    "description": "It's something!",
    "invertedIndexConfig": {
        "bm25": {"b": 0.8, "k1": 1.3},
        "cleanupIntervalSeconds": 61,
        "indexPropertyLength": True,
        "indexTimestamps": True,
        "stopwords": {"additions": None, "preset": "en", "removals": ["the"]},
    },
    "moduleConfig": {
        "generative-openai": {},
        "text2vec-contextionary": {"vectorizeClassName": True},
    },
    "multiTenancyConfig": {
        "autoTenantActivation": False,
        "autoTenantCreation": False,
        "enabled": False,
    },
    "properties": [
        {
            "dataType": ["text[]"],
            "indexFilterable": True,
            "indexRangeFilters": False,
            "indexSearchable": True,
            "moduleConfig": {
                "text2vec-contextionary": {"skip": False, "vectorizePropertyName": False}
            },
            "name": "names",
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
    "vectorIndexConfig": {
        "skip": True,
        "cleanupIntervalSeconds": 300,
        "maxConnections": 64,
        "efConstruction": 128,
        "ef": -2,
        "dynamicEfMin": 101,
        "dynamicEfMax": 501,
        "dynamicEfFactor": 9,
        "vectorCacheMaxObjects": 1000000000001,
        "flatSearchCutoff": 40001,
        "distance": "cosine",
        "pq": {
            "enabled": True,
            "bitCompression": True,
            "segments": 1,
            "centroids": 257,
            "trainingLimit": 100001,
            "encoder": {"type": "tile", "distribution": "normal"},
        },
        "bq": {"enabled": False},
        "sq": {"enabled": False, "trainingLimit": 100000, "rescoreLimit": 20},
    },
    "vectorIndexType": "hnsw",
    "vectorizer": "text2vec-contextionary",
}
