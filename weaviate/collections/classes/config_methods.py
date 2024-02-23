from typing import Any, Dict, List, Optional, Union, cast

from weaviate.collections.classes.config import (
    _BQConfig,
    _CollectionConfig,
    _CollectionConfigSimple,
    _NamedVectorConfig,
    _NamedVectorizerConfig,
    _PQConfig,
    _VectorIndexConfigFlat,
    _InvertedIndexConfig,
    _BM25Config,
    _StopwordsConfig,
    _MultiTenancyConfig,
    _Property,
    _ReferenceProperty,
    _ReplicationConfig,
    _ShardingConfig,
    _VectorIndexConfigHNSW,
    StopwordsPreset,
    VectorDistances,
    PQEncoderType,
    PQEncoderDistribution,
    VectorIndexType,
    Vectorizers,
    Tokenization,
    _PQEncoderConfig,
    _PropertyVectorizerConfig,
    _VectorizerConfig,
    _GenerativeConfig,
    GenerativeSearches,
    DataType,
    _RerankerConfig,
    Rerankers,
    _NestedProperty,
)


def _is_primitive(d_type: str) -> bool:
    return d_type[0][0].lower() == d_type[0][0]


def __get_rerank_config(schema: Dict[str, Any]) -> Optional[_RerankerConfig]:
    if (
        len(
            rerankers := [key for key in schema.get("moduleConfig", {}).keys() if "reranker" in key]
        )
        == 1
    ):
        return _RerankerConfig(
            model=schema["moduleConfig"][rerankers[0]],
            reranker=Rerankers(rerankers[0]),
        )
    else:
        return None


def __get_generative_config(schema: Dict[str, Any]) -> Optional[_GenerativeConfig]:
    if (
        len(
            generators := [
                key for key in schema.get("moduleConfig", {}).keys() if "generative" in key
            ]
        )
        == 1
    ):
        return _GenerativeConfig(
            generative=GenerativeSearches(generators[0]),
            model=schema["moduleConfig"][generators[0]],
        )
    else:
        return None


def __get_vectorizer_config(schema: Dict[str, Any]) -> Optional[_VectorizerConfig]:
    if __get_vectorizer(schema) is not None and schema.get("vectorizer", "none") != "none":
        vec_config: Dict[str, Any] = schema["moduleConfig"].pop(schema["vectorizer"])
        return _VectorizerConfig(
            vectorize_collection_name=vec_config.pop("vectorizeClassName", False),
            model=vec_config,
            vectorizer=Vectorizers(schema["vectorizer"]),
        )
    else:
        return None


def __get_vectorizer(schema: Dict[str, Any]) -> Optional[Vectorizers]:
    # ignore single vectorizer config if named vectors are present
    if "vectorConfig" in schema:
        return None
    return Vectorizers(schema.get("vectorizer"))


def __get_vector_index_type(schema: Dict[str, Any]) -> Optional[VectorIndexType]:
    if "vectorIndexType" in schema:
        return VectorIndexType(schema["vectorIndexType"])
    else:
        return None


def __get_vector_index_config(
    schema: Dict[str, Any]
) -> Union[_VectorIndexConfigHNSW, _VectorIndexConfigFlat, None]:
    if "vectorIndexConfig" not in schema:
        return None
    quantizer: Optional[Union[_PQConfig, _BQConfig]] = None
    if "bq" in schema["vectorIndexConfig"] and schema["vectorIndexConfig"]["bq"]["enabled"]:
        # values are not present for bq+hnsw
        quantizer = _BQConfig(
            cache=schema["vectorIndexConfig"]["bq"].get("cache"),
            rescore_limit=schema["vectorIndexConfig"]["bq"].get("rescoreLimit"),
        )
    elif "pq" in schema["vectorIndexConfig"] and schema["vectorIndexConfig"]["pq"]["enabled"]:
        quantizer = _PQConfig(
            bit_compression=schema["vectorIndexConfig"]["pq"]["bitCompression"],
            segments=schema["vectorIndexConfig"]["pq"]["segments"],
            centroids=schema["vectorIndexConfig"]["pq"]["centroids"],
            training_limit=schema["vectorIndexConfig"]["pq"]["trainingLimit"],
            encoder=_PQEncoderConfig(
                type_=PQEncoderType(schema["vectorIndexConfig"]["pq"]["encoder"]["type"]),
                distribution=PQEncoderDistribution(
                    schema["vectorIndexConfig"]["pq"]["encoder"]["distribution"]
                ),
            ),
        )

    if schema["vectorIndexType"] == "hnsw":
        return _VectorIndexConfigHNSW(
            cleanup_interval_seconds=schema["vectorIndexConfig"]["cleanupIntervalSeconds"],
            distance_metric=VectorDistances(schema["vectorIndexConfig"]["distance"]),
            dynamic_ef_min=schema["vectorIndexConfig"]["dynamicEfMin"],
            dynamic_ef_max=schema["vectorIndexConfig"]["dynamicEfMax"],
            dynamic_ef_factor=schema["vectorIndexConfig"]["dynamicEfFactor"],
            ef=schema["vectorIndexConfig"]["ef"],
            ef_construction=schema["vectorIndexConfig"]["efConstruction"],
            flat_search_cutoff=schema["vectorIndexConfig"]["flatSearchCutoff"],
            max_connections=schema["vectorIndexConfig"]["maxConnections"],
            quantizer=quantizer,
            skip=schema["vectorIndexConfig"]["skip"],
            vector_cache_max_objects=schema["vectorIndexConfig"]["vectorCacheMaxObjects"],
        )
    else:
        assert schema["vectorIndexType"] == "flat"
        return _VectorIndexConfigFlat(
            distance_metric=VectorDistances(schema["vectorIndexConfig"]["distance"]),
            quantizer=quantizer,
            vector_cache_max_objects=schema["vectorIndexConfig"]["vectorCacheMaxObjects"],
        )


def __get_vector_config(
    schema: Dict[str, Any], simple: bool
) -> Optional[Dict[str, _NamedVectorConfig]]:
    if "vectorConfig" in schema:
        named_vectors: Dict[str, _NamedVectorConfig] = {}
        for name in schema["vectorConfig"]:
            named_vector = schema["vectorConfig"][name]

            vectorizer = named_vector["vectorizer"].keys()
            assert len(vectorizer) == 1

            vectorizer_str: str = str(list(vectorizer)[0])
            vec_config: Dict[str, Any] = named_vector["vectorizer"][vectorizer_str]
            props = vec_config.pop("properties", None)

            vector_index_config = __get_vector_index_config(named_vector)
            assert vector_index_config is not None

            named_vectors[name] = _NamedVectorConfig(
                vectorizer=_NamedVectorizerConfig(
                    vectorizer=Vectorizers(vectorizer_str),
                    model=vec_config,
                    source_properties=props,
                ),
                vector_index_config=vector_index_config,
            )
        return named_vectors
    else:
        return None


def _collection_config_simple_from_json(schema: Dict[str, Any]) -> _CollectionConfigSimple:
    return _CollectionConfigSimple(
        name=schema["class"],
        description=schema.get("description"),
        generative_config=__get_generative_config(schema),
        properties=_properties_from_config(schema) if schema.get("properties") is not None else [],
        references=_references_from_config(schema) if schema.get("properties") is not None else [],
        reranker_config=__get_rerank_config(schema),
        vectorizer_config=__get_vectorizer_config(schema),
        vectorizer=__get_vectorizer(schema),
        vector_config=__get_vector_config(schema, simple=True),
    )


def _collection_config_from_json(schema: Dict[str, Any]) -> _CollectionConfig:
    return _CollectionConfig(
        name=schema["class"],
        description=schema.get("description"),
        generative_config=__get_generative_config(schema),
        inverted_index_config=_InvertedIndexConfig(
            bm25=_BM25Config(
                b=schema["invertedIndexConfig"]["bm25"]["b"],
                k1=schema["invertedIndexConfig"]["bm25"]["k1"],
            ),
            cleanup_interval_seconds=schema["invertedIndexConfig"]["cleanupIntervalSeconds"],
            index_null_state=cast(dict, schema["invertedIndexConfig"]).get("indexNullState")
            is True,
            index_property_length=cast(dict, schema["invertedIndexConfig"]).get(
                "indexPropertyLength"
            )
            is True,
            index_timestamps=cast(dict, schema["invertedIndexConfig"]).get("indexTimestamps")
            is True,
            stopwords=_StopwordsConfig(
                preset=StopwordsPreset(schema["invertedIndexConfig"]["stopwords"]["preset"]),
                additions=schema["invertedIndexConfig"]["stopwords"]["additions"],
                removals=schema["invertedIndexConfig"]["stopwords"]["removals"],
            ),
        ),
        multi_tenancy_config=_MultiTenancyConfig(
            enabled=schema.get("multiTenancyConfig", {}).get("enabled", False)
        ),
        properties=_properties_from_config(schema) if schema.get("properties") is not None else [],
        references=_references_from_config(schema) if schema.get("properties") is not None else [],
        replication_config=_ReplicationConfig(factor=schema["replicationConfig"]["factor"]),
        reranker_config=__get_rerank_config(schema),
        sharding_config=None
        if schema.get("multiTenancyConfig", {}).get("enabled", False)
        else _ShardingConfig(
            virtual_per_physical=schema["shardingConfig"]["virtualPerPhysical"],
            desired_count=schema["shardingConfig"]["desiredCount"],
            actual_count=schema["shardingConfig"]["actualCount"],
            desired_virtual_count=schema["shardingConfig"]["desiredVirtualCount"],
            actual_virtual_count=schema["shardingConfig"]["actualVirtualCount"],
            key=schema["shardingConfig"]["key"],
            strategy=schema["shardingConfig"]["strategy"],
            function=schema["shardingConfig"]["function"],
        ),
        vector_index_config=__get_vector_index_config(schema),
        vector_index_type=__get_vector_index_type(schema),
        vectorizer_config=__get_vectorizer_config(schema),
        vectorizer=__get_vectorizer(schema),
        vector_config=__get_vector_config(schema, simple=False),
    )


def _collection_configs_from_json(schema: Dict[str, Any]) -> Dict[str, _CollectionConfig]:
    return {schema["class"]: _collection_config_from_json(schema) for schema in schema["classes"]}


def _collection_configs_simple_from_json(
    schema: Dict[str, Any]
) -> Dict[str, _CollectionConfigSimple]:
    return {
        schema["class"]: _collection_config_simple_from_json(schema) for schema in schema["classes"]
    }


def _nested_properties_from_config(props: List[Dict[str, Any]]) -> List[_NestedProperty]:
    return [
        _NestedProperty(
            data_type=DataType(prop["dataType"][0]),
            description=prop.get("description"),
            index_filterable=prop["indexFilterable"],
            index_searchable=prop["indexSearchable"],
            name=prop["name"],
            nested_properties=(
                _nested_properties_from_config(prop["nestedProperties"])
                if prop.get("nestedProperties") is not None
                else None
            ),
            tokenization=(
                Tokenization(prop["tokenization"]) if prop.get("tokenization") is not None else None
            ),
        )
        for prop in props
    ]


def _properties_from_config(schema: Dict[str, Any]) -> List[_Property]:
    return [
        _Property(
            data_type=DataType(prop["dataType"][0]),
            description=prop.get("description"),
            index_filterable=prop["indexFilterable"],
            index_searchable=prop["indexSearchable"],
            name=prop["name"],
            nested_properties=(
                _nested_properties_from_config(prop["nestedProperties"])
                if prop.get("nestedProperties") is not None
                else None
            ),
            tokenization=(
                Tokenization(prop["tokenization"]) if prop.get("tokenization") is not None else None
            ),
            vectorizer_config=(
                _PropertyVectorizerConfig(
                    skip=prop["moduleConfig"][schema["vectorizer"]].get("skip", False),
                    vectorize_property_name=prop["moduleConfig"][schema["vectorizer"]].get(
                        "vectorizePropertyName", False
                    ),
                )
                if schema.get("vectorizer", "none") != "none"
                else None
            ),
            vectorizer=schema.get("vectorizer", "none"),
        )
        for prop in schema["properties"]
        if _is_primitive(prop["dataType"])
    ]


def _references_from_config(schema: Dict[str, Any]) -> List[_ReferenceProperty]:
    return [
        _ReferenceProperty(
            target_collections=prop["dataType"],
            description=prop.get("description"),
            name=prop["name"],
        )
        for prop in schema["properties"]
        if not _is_primitive(prop["dataType"])
    ]
