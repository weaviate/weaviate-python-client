import asyncio
import time
from enum import Enum
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
    overload,
)

from httpx import Response
from pydantic_core import ValidationError
from typing_extensions import deprecated

from weaviate.collections.classes.config import (
    BM25Algorithm,
    CollectionConfig,
    CollectionConfigSimple,
    CollectionInvertedIndexes,
    IndexName,
    InvertedIndexState,
    InvertedIndexStatus,
    InvertedIndexTask,
    InvertedIndexType,
    Property,
    PropertyType,
    ReferenceProperty,
    ShardStatus,
    ShardTypes,
    Tokenization,
    _CollectionConfigUpdate,
    _GenerativeProvider,
    _InvertedIndexConfigUpdate,
    _MultiTenancyConfigUpdate,
    _NamedVectorConfigCreate,
    _NamedVectorConfigUpdate,
    _ReferencePropertyMultiTarget,
    _ReplicationConfigUpdate,
    _RerankerProvider,
    _ShardStatus,
    _VectorConfigCreate,
    _VectorConfigUpdate,
    _VectorIndexConfigFlatUpdate,
    _VectorIndexConfigHFreshUpdate,
    _VectorIndexConfigHNSWUpdate,
)
from weaviate.collections.classes.config_methods import (
    _collection_config_from_json,
    _collection_config_simple_from_json,
    _collection_inverted_indexes_from_json,
    _inverted_index_task_from_json,
)
from weaviate.collections.classes.config_object_ttl import _ObjectTTLConfigUpdate
from weaviate.collections.classes.config_vector_index import (
    _VectorIndexConfigDynamicUpdate,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync, ConnectionType, _ExpectedStatusCodes
from weaviate.exceptions import (
    ReindexCanceledError,
    ReindexFailedError,
    ReindexTimeoutError,
    WeaviateInvalidInputError,
    WeaviateUnsupportedFeatureError,
)
from weaviate.util import (
    _capitalize_first_letter,
    _decode_json_response_dict,
    _decode_json_response_list,
)
from weaviate.validator import _validate_input, _ValidateArgument
from weaviate.warnings import _Warnings


def _any_property_has_text_analyzer(properties: Sequence[Property]) -> bool:
    return any(_property_has_text_analyzer(p) for p in properties)


def _property_has_text_analyzer(prop: Property) -> bool:
    if prop.textAnalyzer is not None:
        return True
    nested = prop.nestedProperties
    if nested is None:
        return False
    nested_list = nested if isinstance(nested, list) else [nested]
    return any(_property_has_text_analyzer(np) for np in nested_list)


def _find_property_index_status(
    indexes: CollectionInvertedIndexes, property_name: str, index_name: IndexName
) -> Optional[InvertedIndexStatus]:
    for prop in indexes.properties:
        if prop.name != property_name:
            continue
        for index in prop.indexes:
            if index.type == index_name:
                return index
    return None


# A rebuild has no observable end-state on the index projection (the configuration does not
# change), so its wait is best-effort: if the task is never seen active, accept a ready entry after
# this many consecutive ready polls. We cannot positively observe a rebuild's completion, so a
# rebuild whose task is still queued on a lagging RAFT follower could report done up to roughly
# this many seconds early (dirkkul's original race, bounded). Kept generous to tolerate read lag.
_REINDEX_REBUILD_READY_GRACE_POLLS = 10

# No-progress bound: if the index entry stops advancing toward the requested state (vanishes, or
# sits ready on the OLD config) for this many consecutive polls, give up rather than hang forever
# (a server-side fault, e.g. an incomplete swap). Set well above RAFT read-lag and any brief
# transition window so a healthy migration NEVER trips it (any progressing poll resets the count).
_REINDEX_STALL_POLLS = 30

# Seconds between index-status polls. A module constant so tests can shrink it.
_REINDEX_POLL_INTERVAL_SECONDS = 1.0


def _enum_value(value: Any) -> Any:
    """Normalize a str-enum (Tokenization / BM25Algorithm) to its wire string for comparison."""
    return value.value if isinstance(value, Enum) else value


def _reindex_converged(
    entry: InvertedIndexStatus,
    expected_tokenization: Optional[str],
    expected_algorithm: Optional[str],
    is_rebuild: bool,
    task_seen_active: bool,
    ready_polls: int,
) -> bool:
    """Decide whether a READY index ``entry`` reflects the completion of the submitted request.

    Caller guarantees ``entry.state == READY``. Compares by wire-string value so an enum-vs-string
    mismatch cannot cause a false negative.
    """
    # A migration still in flight shows its target in these fields (finalize / pre-flip window).
    if entry.target_tokenization is not None or entry.target_algorithm is not None:
        return False
    if expected_tokenization is not None:
        # A stale pre-flip ready still carries the OLD tokenization, so this won't match early.
        return _enum_value(entry.tokenization) == expected_tokenization
    if expected_algorithm is not None:
        return _enum_value(entry.algorithm) == expected_algorithm
    if is_rebuild:
        # No visible end-state: accept once we saw the task active, or after a small ready grace.
        return task_seen_active or ready_polls >= _REINDEX_REBUILD_READY_GRACE_POLLS
    # A create with an empty body ({}) that returned 202: the index now exists and is ready.
    return True


class _ConfigCollectionExecutor(Generic[ConnectionType]):
    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        tenant: Optional[str] = None,
    ) -> None:
        self._connection = connection
        self._name = name
        self._tenant = tenant

    def __get(self) -> executor.Result[Dict[str, Any]]:
        def resp(res: Response) -> Dict[str, Any]:
            return cast(Dict[str, Any], res.json())

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=f"/schema/{self._name}",
            error_msg="Collection configuration could not be retrieved.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Get collection configuration"),
        )

    @overload
    def get(
        self,
        simple: Literal[False] = False,
    ) -> executor.Result[CollectionConfig]: ...

    @overload
    def get(
        self,
        simple: Literal[True],
    ) -> executor.Result[CollectionConfigSimple]: ...

    @overload
    def get(
        self,
        simple: bool = False,
    ) -> executor.Result[Union[CollectionConfig, CollectionConfigSimple]]: ...

    def get(
        self,
        simple: bool = False,
    ) -> executor.Result[Union[CollectionConfig, CollectionConfigSimple]]:
        """Get the configuration for this collection from Weaviate.

        Args:
            simple: If True, return a simplified version of the configuration containing only name and properties.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        _validate_input([_ValidateArgument(expected=[bool], name="simple", value=simple)])

        def resp(res: Dict[str, Any]) -> Union[CollectionConfig, CollectionConfigSimple]:
            if simple:
                return _collection_config_simple_from_json(res)
            return _collection_config_from_json(res)

        return executor.execute(
            response_callback=resp,
            method=self.__get,
        )

    def update(
        self,
        *,
        description: Optional[str] = None,
        property_descriptions: Optional[Dict[str, str]] = None,
        inverted_index_config: Optional[_InvertedIndexConfigUpdate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigUpdate] = None,
        object_ttl_config: Optional[_ObjectTTLConfigUpdate] = None,
        replication_config: Optional[_ReplicationConfigUpdate] = None,
        vector_index_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
                _VectorIndexConfigHFreshUpdate,
            ]
        ] = None,
        vectorizer_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
                _VectorIndexConfigDynamicUpdate,
                _VectorIndexConfigHFreshUpdate,
                List[_NamedVectorConfigUpdate],
            ]
        ] = None,
        vector_config: Optional[Union[_VectorConfigUpdate, List[_VectorConfigUpdate]]] = None,
        generative_config: Optional[_GenerativeProvider] = None,
        reranker_config: Optional[_RerankerProvider] = None,
    ) -> executor.Result[None]:
        """Update the configuration for this collection in Weaviate.

        Use the `weaviate.classes.Reconfigure` class to generate the necessary configuration objects for this method.

        Args:
            description: A description of the collection.
            inverted_index_config: Configuration for the inverted index. Use `Reconfigure.inverted_index` to generate one.
            multi_tenancy_config: Configuration for multi-tenancy settings. Use `Reconfigure.multi_tenancy` to generate one.
                Only `auto_tenant_creation` is supported.
            object_ttl_config: Configuration for object TTL settings. Use `Reconfigure.object_ttl` to generate one.
            replication_config: Configuration for the replication. Use `Reconfigure.replication` to generate one.
            reranker_config: Configuration for the reranker. Use `Reconfigure.replication` to generate one.
            vector_index_config (DEPRECATED use `vector_config`): Configuration for the vector index of the default single vector. Use `Reconfigure.vector_index` to generate one.
            vectorizer_config: Configurations for the vector index (or indices) of your collection.
                Use `Reconfigure.vector_index` if using legacy vectorization and `Reconfigure.NamedVectors` if you have many named vectors to generate them.
                Using this argument with a list of `Reconfigure.NamedVectors` is **DEPRECATED**. Use the `vector_config` argument instead in such a case.
            vector_config: Configuration for the vector index (or indices) of your collection.
                Use `Reconfigure.Vectors` for both single and multiple vectorizers. Supply a list to update many vectorizers at once.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.

        NOTE:
            - If you wish to update a specific option within the configuration and cannot find it in `CollectionConfigUpdate` then it is an immutable option.
            - To change it, you will have to delete the collection and recreate it with the desired options.
            - This is not the case of adding properties, which can be done with `collection.config.add_property()`.
        """
        if vector_index_config is not None:
            _Warnings.vector_index_config_in_config_update()
        if vectorizer_config is not None and not isinstance(
            vectorizer_config,
            (
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
                _VectorIndexConfigDynamicUpdate,
                _VectorIndexConfigHFreshUpdate,
            ),
        ):
            _Warnings.vectorizer_config_in_config_update()
        if (
            inverted_index_config is not None
            and inverted_index_config.stopwordPresets is not None
            and not self._connection._weaviate_version.is_at_least(1, 37, 0)
        ):
            raise WeaviateUnsupportedFeatureError(
                "InvertedIndexConfig stopword_presets",
                str(self._connection._weaviate_version),
                "1.37.0",
            )
        try:
            config = _CollectionConfigUpdate(
                description=description,
                property_descriptions=property_descriptions,
                inverted_index_config=inverted_index_config,
                replication_config=replication_config,
                vector_index_config=vector_index_config,
                vectorizer_config=vectorizer_config,
                object_ttl_config=object_ttl_config,
                multi_tenancy_config=multi_tenancy_config,
                generative_config=generative_config,
                reranker_config=reranker_config,
                vector_config=vector_config,
            )
        except ValidationError as e:
            raise WeaviateInvalidInputError("Invalid collection config update parameters.") from e

        def resp(schema: Dict[str, Any]) -> executor.Result[None]:
            schema = config.merge_with_existing(schema)

            def inner_resp(res: Response) -> None:
                return None

            return executor.execute(
                response_callback=inner_resp,
                method=self._connection.put,
                path=f"/schema/{self._name}",
                weaviate_object=schema,
                error_msg="Collection configuration may not have been updated.",
                status_codes=_ExpectedStatusCodes(
                    ok_in=200, error="Update collection configuration"
                ),
            )

        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> None:
                schema = await executor.aresult(self.__get())
                return await executor.aresult(resp(schema))

            return _execute()
        schema = executor.result(self.__get())
        return executor.result(resp(schema))

    def __add_property(self, additional_property: PropertyType) -> executor.Result[None]:
        if isinstance(additional_property, Property) and _property_has_text_analyzer(
            additional_property
        ):
            if not self._connection._weaviate_version.is_at_least(1, 37, 0):
                raise WeaviateUnsupportedFeatureError(
                    "Property text_analyzer (asciiFold)",
                    str(self._connection._weaviate_version),
                    "1.37.0",
                )
        path = f"/schema/{self._name}/properties"
        obj = additional_property._to_dict()

        def resp(schema: Dict[str, Any]) -> executor.Result[None]:
            modconf = {}
            if "skip_vectorization" in obj:
                modconf["skip"] = obj["skip_vectorization"]
                del obj["skip_vectorization"]

            if "vectorize_property_name" in obj:
                modconf["vectorizePropertyName"] = obj["vectorize_property_name"]
                del obj["vectorize_property_name"]

            module_config: Dict[str, Any] = schema.get("moduleConfig", {})
            legacy_vectorizer = [
                str(k) for k in module_config if "generative" not in k and "reranker" not in k
            ]
            if len(legacy_vectorizer) > 0 and len(modconf) > 0:
                obj["moduleConfig"] = {legacy_vectorizer[0]: modconf}

            vector_config: Dict[str, Any] = schema.get("vectorConfig", {})
            if len(vector_config) > 0:
                obj["moduleConfig"] = {
                    list(conf["vectorizer"].keys()).pop(): modconf
                    for conf in vector_config.values()
                }

            def inner_resp(res: Response) -> None:
                return None

            return executor.execute(
                response_callback=inner_resp,
                method=self._connection.post,
                path=path,
                weaviate_object=obj,
                error_msg="Property may not have been added properly.",
                status_codes=_ExpectedStatusCodes(ok_in=200, error="Add property to collection"),
            )

        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> None:
                schema = await executor.aresult(self.__get())
                return await executor.aresult(resp(schema))

            return _execute()
        schema = executor.result(self.__get())
        return executor.result(resp(schema))

    def __property_exists(self, property_name: str) -> executor.Result[bool]:
        def resp(schema: Dict[str, Any]) -> bool:
            conf = _collection_config_simple_from_json(schema)
            if len(conf.properties) == 0:
                return False
            for prop in conf.properties:
                if prop.name == property_name:
                    return True
            return False

        return executor.execute(
            response_callback=resp,
            method=self.__get,
        )

    def __reference_exists(self, reference_name: str) -> executor.Result[bool]:
        def resp(schema: Dict[str, Any]) -> bool:
            conf = _collection_config_simple_from_json(schema)
            if len(conf.references) == 0:
                return False
            for ref in conf.references:
                if ref.name == reference_name:
                    return True
            return False

        return executor.execute(
            response_callback=resp,
            method=self.__get,
        )

    def __get_shards(self) -> executor.Result[List[ShardStatus]]:
        def resp(res: Response) -> List[ShardStatus]:
            shards = _decode_json_response_list(res, "get shards")
            assert shards is not None
            return [
                _ShardStatus(
                    name=shard["name"],
                    status=shard["status"],
                    vector_queue_size=shard["vectorQueueSize"],
                )
                for shard in shards
            ]

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=f"/schema/{self._name}/shards{f'?tenant={self._tenant}' if self._tenant else ''}",
            error_msg="Shard statuses could not be retrieved.",
        )

    def get_shards(self) -> executor.Result[List[ShardStatus]]:
        """Get the statuses of the shards of this collection.

        If the collection is multi-tenancy and you did not call `.with_tenant` then you
        will receive the statuses of all the tenants within the collection. Otherwise, call
        `.with_tenant` on the collection first and you will receive only that single shard.

        Returns:
            A list of objects containing the statuses of the shards.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        return self.__get_shards()

    def __update_shard(
        self, shard_name: str, status: str
    ) -> executor.Result[Tuple[str, ShardTypes]]:
        path = f"/schema/{self._name}/shards/{shard_name}"
        data = {"status": status}

        def resp(res: Response) -> Tuple[str, ShardTypes]:
            shard = _decode_json_response_dict(res, f"Update shard '{shard_name}' status")
            assert shard is not None
            return shard_name, shard["status"]

        return executor.execute(
            response_callback=resp,
            method=self._connection.put,
            path=path,
            weaviate_object=data,
            error_msg=f"shard '{shard_name}' may not have been updated.",
        )

    def update_shards(
        self,
        status: Literal["READY", "READONLY"],
        shard_names: Optional[Union[str, List[str]]] = None,
    ) -> executor.Result[Dict[str, ShardTypes]]:
        """Update the status of one or all shards of this collection.

        Args:
            status: The new status of the shard. The available options are: 'READY' and 'READONLY'.
            shard_name: The shard name for which to update the status of the class of the shard. If None all shards are going to be updated.

        Returns:
            All updated shards indexed by their name.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        if isinstance(self._connection, ConnectionAsync):

            async def _execute(
                shard_names: Optional[Union[str, List[str]]],
            ) -> Dict[str, ShardTypes]:
                if shard_names is None:
                    shards_config = await executor.aresult(self.__get_shards())
                    shard_names = [shard_config.name for shard_config in shards_config]
                elif isinstance(shard_names, str):
                    shard_names = [shard_names]

                results = await asyncio.gather(
                    *[
                        executor.aresult(self.__update_shard(shard_name=shard_name, status=status))
                        for shard_name in shard_names
                    ]
                )

                return {result[0]: result[1] for result in results}

            return _execute(shard_names)

        if shard_names is None:
            shards_config = executor.result(self.__get_shards())
            shard_names = [shard_config.name for shard_config in shards_config]
        elif isinstance(shard_names, str):
            shard_names = [shard_names]

        return {
            result[0]: result[1]
            for result in [
                executor.result(self.__update_shard(shard_name=shard_name, status=status))
                for shard_name in shard_names
            ]
        }

    def add_property(self, prop: Property) -> executor.Result[None]:
        """Add a property to the collection in Weaviate.

        Args:
            prop: The property to add to the collection.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
            weaviate.exceptions.WeaviateInvalidInputError: If the property already exists in the collection.
        """
        _validate_input([_ValidateArgument(expected=[Property], name="prop", value=prop)])

        def resp(exists: bool) -> executor.Result[None]:
            if exists:
                raise WeaviateInvalidInputError(
                    f"Property with name '{prop.name}' already exists in collection '{self._name}'."
                )
            return self.__add_property(additional_property=prop)

        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> None:
                exists = await executor.aresult(self.__property_exists(property_name=prop.name))
                return await executor.aresult(resp(exists))

            return _execute()
        exists = executor.result(self.__property_exists(property_name=prop.name))
        return executor.result(resp(exists))

    def add_reference(
        self,
        ref: Union[ReferenceProperty, _ReferencePropertyMultiTarget],
    ) -> executor.Result[None]:
        """Add a reference to the collection in Weaviate.

        Args:
            ref: The reference to add to the collection.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
            weaviate.exceptions.WeaviateInvalidInputError: If the reference already exists in the collection.
        """
        _validate_input(
            [
                _ValidateArgument(
                    expected=[ReferenceProperty, _ReferencePropertyMultiTarget],
                    name="ref",
                    value=ref,
                )
            ]
        )

        def resp(exists: bool) -> executor.Result[None]:
            if exists:
                raise WeaviateInvalidInputError(
                    f"Reference with name '{ref.name}' already exists in collection '{self._name}'."
                )
            return self.__add_property(additional_property=ref)

        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> None:
                exists = await executor.aresult(self.__reference_exists(reference_name=ref.name))
                return await executor.aresult(resp(exists))

            return _execute()
        exists = executor.result(self.__reference_exists(reference_name=ref.name))
        return executor.result(resp(exists))

    @overload
    @deprecated(
        "Using `Configure.NamedVectors` in `vector_config` is deprecated. Instead, use `Configure.Vectors` or `Configure.MultiVectors`."
    )
    def add_vector(
        self, *, vector_config: Union[_NamedVectorConfigCreate, List[_NamedVectorConfigCreate]]
    ) -> executor.Result[None]: ...

    @overload
    def add_vector(
        self, *, vector_config: Union[_VectorConfigCreate, List[_VectorConfigCreate]]
    ) -> executor.Result[None]: ...

    def add_vector(
        self,
        *,
        vector_config: Union[
            _NamedVectorConfigCreate,
            _VectorConfigCreate,
            List[_NamedVectorConfigCreate],
            List[_VectorConfigCreate],
        ],
    ) -> executor.Result[None]:
        """Add a vector to the collection in Weaviate.

        Args:
            vector_config: The vector configuration to add to the collection.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
            weaviate.exceptions.WeaviateInvalidInputError: If the vector already exists in the collection.
        """
        _validate_input(
            [
                _ValidateArgument(
                    expected=[
                        _NamedVectorConfigCreate,
                        _VectorConfigCreate,
                        List[_NamedVectorConfigCreate],
                        List[_VectorConfigCreate],
                    ],
                    name="vector_config",
                    value=vector_config,
                )
            ]
        )
        if isinstance(vector_config, list):
            for c in vector_config:
                if isinstance(c, _NamedVectorConfigCreate):
                    _Warnings.named_vector_syntax_in_config_add_vector(c.name)
                if c.name is None:
                    raise WeaviateInvalidInputError(
                        "The configured vector must have a name when adding it to a collection."
                    )
        if isinstance(vector_config, _NamedVectorConfigCreate):
            _Warnings.named_vector_syntax_in_config_add_vector(vector_config.name)
            vector_config = [vector_config]
        if isinstance(vector_config, _VectorConfigCreate):
            vector_config = [vector_config]

        def resp(schema: Dict[str, Any]) -> executor.Result[None]:
            if "vectorConfig" not in schema:
                schema["vectorConfig"] = {}
            for vector in vector_config:
                schema["vectorConfig"][vector.name] = vector._to_dict()

            return executor.execute(
                response_callback=lambda _: None,
                method=self._connection.put,
                path=f"/schema/{self._name}",
                weaviate_object=schema,
                error_msg="Collection configuration may not have been updated.",
                status_codes=_ExpectedStatusCodes(
                    ok_in=200, error="Update collection configuration"
                ),
            )

        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> None:
                schema = await executor.aresult(self.__get())
                return await executor.aresult(resp(schema))

            return _execute()
        schema = executor.result(self.__get())
        return executor.result(resp(schema))

    def delete_property_index(
        self,
        property_name: str,
        index_name: Union[InvertedIndexType, IndexName],
    ) -> executor.Result[bool]:
        """Delete a property index from the collection in Weaviate.

            This is a destructive operation. The index will
            need to be regenerated if you wish to use it again.

        Args:
            property_name: The property name from which to delete the index.
            index_name: The type of the index to delete, an `InvertedIndexType` value. Passing a
                raw string (`searchable`, `filterable` or `rangeFilters`) is deprecated but still
                accepted.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
            weaviate.exceptions.WeaviateInvalidInputError: If the property or index does not exist.
        """
        if not isinstance(index_name, InvertedIndexType):
            _Warnings.string_index_name_is_deprecated()
        index = cast(
            IndexName,
            index_name.value if isinstance(index_name, InvertedIndexType) else index_name,
        )
        _validate_input(
            [_ValidateArgument(expected=[str], name="property_name", value=property_name)]
        )
        _validate_input([_ValidateArgument(expected=[str], name="index_name", value=index)])

        path = self.__property_index_path(property_name, index)

        def resp(res: Response) -> bool:
            return res.status_code == 200

        return executor.execute(
            response_callback=resp,
            method=self._connection.delete,
            path=path,
            error_msg="Property index may not have been deleted.",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Delete property index"),
        )

    def __check_property_reindex_support(self, feature: str) -> None:
        if not self._connection._weaviate_version.is_at_least(1, 39, 0):
            raise WeaviateUnsupportedFeatureError(
                feature,
                str(self._connection._weaviate_version),
                "1.39.0",
            )

    def __property_index_path(self, property_name: str, index_name: IndexName) -> str:
        return (
            f"/schema/{_capitalize_first_letter(self._name)}"
            + f"/properties/{property_name}"
            + f"/index/{index_name}"
        )

    def __wait_for_property_index(
        self,
        property_name: str,
        index_name: IndexName,
        task: InvertedIndexTask,
        timeout: Optional[float],
        expected_tokenization: Optional[str],
        expected_algorithm: Optional[str],
        is_rebuild: bool,
    ) -> executor.Result[InvertedIndexStatus]:
        """Poll GET /schema/{class}/indexes until the submitted request converges, then return it.

        The index status endpoint is the completion signal (it authorizes on collection metadata,
        the same access as the reindex operation itself, and strips the caller namespace from the
        entry's ``task_id``). A ``NO_OP`` submission (no task id) means the configuration already
        matched, so the current status is fetched once and returned without polling. Otherwise poll
        every second: FAILED/CANCELLED on our task raise; a READY entry that matches the requested
        state (see ``_reindex_converged``) is returned. The finalize window (``indexing`` at
        progress 1.0) is never treated as done.

        A rebuild has no observable end-state, so its wait is best-effort: it returns once the entry
        has been ready (having seen the task active, or after a consecutive-ready grace).

        The wait is bounded two ways: an explicit ``timeout`` (total seconds), and a no-progress
        guard - if the entry stops advancing toward the requested state (vanishes, or sits ready on
        the old config) for ``_REINDEX_STALL_POLLS`` consecutive polls, ``ReindexTimeoutError`` is
        raised rather than hanging forever on a server-side fault. Any progressing poll resets it.
        """
        task_id = task.task_id

        def deadline() -> Optional[float]:
            return time.monotonic() + timeout if timeout is not None else None

        timeout_error = ReindexTimeoutError(
            f"Timed out after {timeout}s waiting for the reindex of the '{index_name}' index of "
            f"property '{property_name}' (task '{task_id}') to complete. Poll "
            f"collection.config.get_property_indexes() to check on it."
        )
        stall_error = ReindexTimeoutError(
            f"The reindex of the '{index_name}' index of property '{property_name}' (task "
            f"'{task_id}') did not progress toward the requested state and its entry is no longer "
            f"advancing (the task may have failed server-side, e.g. an incomplete swap). Could not "
            f"confirm completion; inspect collection.config.get_property_indexes() and GET /v1/tasks."
        )
        no_op_missing_error = ReindexFailedError(
            f"The configuration already matched (NO_OP) but the '{index_name}' index of property "
            f"'{property_name}' is not present in get_property_indexes()."
        )

        def check(entry: Optional[InvertedIndexStatus], ready_polls: int) -> Tuple[int, bool]:
            """Classify one poll. Returns (ready_polls, task_seen_active_this_poll).

            Raises on a failed/cancelled entry that belongs to our task.
            """
            if entry is None:
                return 0, False
            seen_active = entry.task_id == task_id
            if seen_active and entry.state == InvertedIndexState.FAILED:
                raise ReindexFailedError(
                    f"Reindexing the '{index_name}' index of property '{property_name}' failed "
                    f"(task '{task_id}'). Inspect collection.config.get_property_indexes() for detail."
                )
            if seen_active and entry.state == InvertedIndexState.CANCELLED:
                raise ReindexCanceledError(
                    f"Reindexing the '{index_name}' index of property '{property_name}' was "
                    f"cancelled (task '{task_id}')."
                )
            if entry.state == InvertedIndexState.READY:
                ready_polls += 1
            else:
                ready_polls = 0
            return ready_polls, seen_active

        def stalled(entry: Optional[InvertedIndexStatus], seen: bool) -> bool:
            """Whether this poll counts as no-progress toward the requested state.

            Reset (returns False) when actively progressing: entry PENDING/INDEXING, or our task is
            seen active. A ready rebuild entry (no requested config change) is left to the ready
            grace, not counted as a stall. Otherwise - entry vanished, or a ready entry still on the
            old config for a requested change - it is a stall.
            """
            if entry is not None and (
                seen or entry.state in (InvertedIndexState.PENDING, InvertedIndexState.INDEXING)
            ):
                return False
            if entry is not None and is_rebuild and entry.state == InvertedIndexState.READY:
                return False
            return True

        converged_args = (expected_tokenization, expected_algorithm, is_rebuild)

        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> InvertedIndexStatus:
                if task_id is None:
                    indexes = await executor.aresult(self.get_property_indexes())
                    entry = _find_property_index_status(indexes, property_name, index_name)
                    if entry is None:
                        raise no_op_missing_error
                    return entry
                limit = deadline()
                task_seen_active = False
                ready_polls = 0
                stall_polls = 0
                while True:
                    indexes = await executor.aresult(self.get_property_indexes())
                    entry = _find_property_index_status(indexes, property_name, index_name)
                    ready_polls, seen = check(entry, ready_polls)
                    task_seen_active = task_seen_active or seen
                    if (
                        entry is not None
                        and entry.state == InvertedIndexState.READY
                        and _reindex_converged(
                            entry, *converged_args, task_seen_active, ready_polls
                        )
                    ):
                        return entry
                    stall_polls = stall_polls + 1 if stalled(entry, seen) else 0
                    if stall_polls >= _REINDEX_STALL_POLLS:
                        raise stall_error
                    if limit is not None:
                        remaining = limit - time.monotonic()
                        if remaining <= 0:
                            raise timeout_error
                        await asyncio.sleep(min(_REINDEX_POLL_INTERVAL_SECONDS, remaining))
                    else:
                        await asyncio.sleep(_REINDEX_POLL_INTERVAL_SECONDS)

            return _execute()

        if task_id is None:
            indexes = executor.result(self.get_property_indexes())
            entry = _find_property_index_status(indexes, property_name, index_name)
            if entry is None:
                raise no_op_missing_error
            return entry
        limit = deadline()
        task_seen_active = False
        ready_polls = 0
        stall_polls = 0
        while True:
            indexes = executor.result(self.get_property_indexes())
            entry = _find_property_index_status(indexes, property_name, index_name)
            ready_polls, seen = check(entry, ready_polls)
            task_seen_active = task_seen_active or seen
            if (
                entry is not None
                and entry.state == InvertedIndexState.READY
                and _reindex_converged(entry, *converged_args, task_seen_active, ready_polls)
            ):
                return entry
            stall_polls = stall_polls + 1 if stalled(entry, seen) else 0
            if stall_polls >= _REINDEX_STALL_POLLS:
                raise stall_error
            if limit is not None:
                remaining = limit - time.monotonic()
                if remaining <= 0:
                    raise timeout_error
                time.sleep(min(_REINDEX_POLL_INTERVAL_SECONDS, remaining))
            else:
                time.sleep(_REINDEX_POLL_INTERVAL_SECONDS)

    def __submit_property_index_task(
        self,
        *,
        property_name: str,
        index_name: IndexName,
        path_suffix: str,
        http_method: Literal["PUT", "POST"],
        body: Dict[str, Any],
        tenants: Union[List[str], str, None],
        wait_for_completion: bool,
        timeout: Optional[float],
        error_verb: str,
        error_label: str,
        ok_in: List[int],
    ) -> executor.Result[Union[InvertedIndexTask, InvertedIndexStatus]]:
        """Submit a reindex task (PUT upsert or POST rebuild) and optionally wait for it.

        Shared by ``update_property_index`` and ``rebuild_property_index``: input validation,
        tenant csv encoding, the sync/async fork and the index-projection wait all live here.
        """
        _validate_input(
            [_ValidateArgument(expected=[str], name="property_name", value=property_name)]
        )
        _validate_input([_ValidateArgument(expected=[str], name="index_name", value=index_name)])
        _validate_input(
            [_ValidateArgument(expected=[str, List[str], None], name="tenants", value=tenants)]
        )
        _validate_input(
            [
                _ValidateArgument(
                    expected=[bool], name="wait_for_completion", value=wait_for_completion
                )
            ]
        )
        _validate_input(
            [_ValidateArgument(expected=[int, float, None], name="timeout", value=timeout)]
        )

        path = self.__property_index_path(property_name, index_name) + path_suffix
        if isinstance(tenants, str):
            tenants = [tenants]
        # An empty tenant selection means "all tenants"; send no param rather than ?tenants= .
        params: Optional[Dict[str, Any]] = {"tenants": ",".join(tenants)} if tenants else None
        error_msg = f"Property index may not have been {error_verb}."
        conn_method = self._connection.put if http_method == "PUT" else self._connection.post
        # What was requested, as wire strings, so the wait can detect convergence on /indexes.
        expected_tokenization = body.get("tokenization")
        expected_algorithm = body.get("algorithm")
        is_rebuild = path_suffix == "/rebuild"

        def resp(res: Response) -> InvertedIndexTask:
            response = _decode_json_response_dict(res, error_label)
            assert response is not None
            return _inverted_index_task_from_json(response)

        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> Union[InvertedIndexTask, InvertedIndexStatus]:
                res = await executor.aresult(
                    conn_method(
                        path=path,
                        weaviate_object=body,
                        params=params,
                        error_msg=error_msg,
                        status_codes=_ExpectedStatusCodes(ok_in=ok_in, error=error_label),
                    )
                )
                task = resp(res)
                if wait_for_completion:
                    return await executor.aresult(
                        self.__wait_for_property_index(
                            property_name,
                            index_name,
                            task,
                            timeout,
                            expected_tokenization,
                            expected_algorithm,
                            is_rebuild,
                        )
                    )
                return task

            return _execute()
        res = executor.result(
            conn_method(
                path=path,
                weaviate_object=body,
                params=params,
                error_msg=error_msg,
                status_codes=_ExpectedStatusCodes(ok_in=ok_in, error=error_label),
            )
        )
        task = resp(res)
        if wait_for_completion:
            return executor.result(
                self.__wait_for_property_index(
                    property_name,
                    index_name,
                    task,
                    timeout,
                    expected_tokenization,
                    expected_algorithm,
                    is_rebuild,
                )
            )
        return task

    @overload
    def update_property_index(
        self,
        property_name: str,
        index_name: InvertedIndexType,
        *,
        tokenization: Optional[Tokenization] = None,
        algorithm: Optional[BM25Algorithm] = None,
        tenants: Union[List[str], str, None] = None,
        wait_for_completion: Literal[True],
        timeout: Optional[float] = None,
    ) -> executor.Result[InvertedIndexStatus]: ...

    @overload
    def update_property_index(
        self,
        property_name: str,
        index_name: InvertedIndexType,
        *,
        tokenization: Optional[Tokenization] = None,
        algorithm: Optional[BM25Algorithm] = None,
        tenants: Union[List[str], str, None] = None,
        wait_for_completion: Literal[False] = False,
        timeout: Optional[float] = None,
    ) -> executor.Result[InvertedIndexTask]: ...

    def update_property_index(
        self,
        property_name: str,
        index_name: InvertedIndexType,
        *,
        tokenization: Optional[Tokenization] = None,
        algorithm: Optional[BM25Algorithm] = None,
        tenants: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        timeout: Optional[float] = None,
    ) -> executor.Result[Union[InvertedIndexTask, InvertedIndexStatus]]:
        """Create or migrate a property index in this collection.

        Note: This method is a declarative upsert operation. If the index does not exist, it is created
        with the requested configuration. If it exists, it is migrated towards the requested
        configuration. If the configuration already matches, no work is submitted and the returned
        task reports a `NO_OP` status. The server accepts at most one configuration change per request.

        Caution: changing `tokenization` via the `searchable` index ALSO retokenizes the property's
        `filterable` index when one exists. Both indexes are migrated by a single coupled task (their
        status entries share one `taskId`), and the retokenization changes how filters match on that
        property. To retokenize only the filterable bucket, target the `filterable` index instead.
        Cancelling via either index type cancels the whole coupled task.

        Args:
            property_name: The property whose index to create or migrate.
            index_name: The type of the index, an `InvertedIndexType` value.
            tokenization: The tokenization of the index. Required when creating a `searchable` index;
                optional as a change on an existing `searchable` or `filterable` index. Not valid for
                `rangeFilters`.
            algorithm: The BM25 scoring algorithm of a `searchable` index. Only
                `BM25Algorithm.BLOCKMAX` is a valid target (the `wand` to `blockmax` migration is
                the only supported transition; the server rejects a request back to `wand`).
            tenants: The tenant/list of tenants for which to create the index. Only valid when
                creating a `rangeFilters` index on a multi-tenant collection. If not provided, all
                tenants are affected.
            wait_for_completion: Whether to poll the index status until the index reports ready for
                the requested configuration. By default False.
            timeout: When `wait_for_completion=True`, the maximum number of seconds to wait. `None`
                (the default) waits while the task keeps progressing; a stalled or vanished task is
                bounded by an internal no-progress guard, after which `ReindexTimeoutError` is raised.

        Returns:
            A `InvertedIndexTask` when `wait_for_completion=False`, or the final `InvertedIndexStatus`
            of the index when `wait_for_completion=True`.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
            weaviate.exceptions.ReindexFailedError: If `wait_for_completion=True` and the reindexing task failed.
            weaviate.exceptions.ReindexCanceledError: If `wait_for_completion=True` and the reindexing task was cancelled.
            weaviate.exceptions.ReindexTimeoutError: If `wait_for_completion=True` and `timeout` is exceeded.
        """
        self.__check_property_reindex_support("Collection config update_property_index")
        # 5d: type validation (keeps enum / wire-string / None leniency, rejects genuine garbage).
        _validate_input(
            [
                _ValidateArgument(
                    expected=[Tokenization, str, None], name="tokenization", value=tokenization
                )
            ]
        )
        _validate_input(
            [
                _ValidateArgument(
                    expected=[BM25Algorithm, str, None], name="algorithm", value=algorithm
                )
            ]
        )
        index = cast(
            IndexName,
            index_name.value if isinstance(index_name, InvertedIndexType) else index_name,
        )
        body: Dict[str, Any] = {}
        if tokenization is not None:
            body["tokenization"] = (
                tokenization.value if isinstance(tokenization, Tokenization) else tokenization
            )
        if algorithm is not None:
            algorithm_value = algorithm.value if isinstance(algorithm, BM25Algorithm) else algorithm
            # 5c: WAND is never a valid target (the server always 400s); reject it clearly.
            if algorithm_value == BM25Algorithm.WAND.value:
                raise WeaviateInvalidInputError(
                    "algorithm=WAND is not a valid target; only BM25Algorithm.BLOCKMAX is supported "
                    "(wand->blockmax is the only transition; downgrade is not supported)."
                )
            body["algorithm"] = algorithm_value
        return self.__submit_property_index_task(
            property_name=property_name,
            index_name=index,
            path_suffix="",
            http_method="PUT",
            body=body,
            tenants=tenants,
            wait_for_completion=wait_for_completion,
            timeout=timeout,
            error_verb="updated",
            error_label="Update property index",
            ok_in=[200, 202],
        )

    @overload
    def rebuild_property_index(
        self,
        property_name: str,
        index_name: InvertedIndexType,
        *,
        tenants: Union[List[str], str, None] = None,
        wait_for_completion: Literal[True],
        timeout: Optional[float] = None,
    ) -> executor.Result[InvertedIndexStatus]: ...

    @overload
    def rebuild_property_index(
        self,
        property_name: str,
        index_name: InvertedIndexType,
        *,
        tenants: Union[List[str], str, None] = None,
        wait_for_completion: Literal[False] = False,
        timeout: Optional[float] = None,
    ) -> executor.Result[InvertedIndexTask]: ...

    def rebuild_property_index(
        self,
        property_name: str,
        index_name: InvertedIndexType,
        *,
        tenants: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        timeout: Optional[float] = None,
    ) -> executor.Result[Union[InvertedIndexTask, InvertedIndexStatus]]:
        """Rebuild an existing property index from scratch with its current configuration.

        Args:
            property_name: The property whose index to rebuild.
            index_name: The type of the index, an `InvertedIndexType` value.
            tenants: The tenant/list of tenants for which to rebuild the index on a multi-tenant
                collection. If not provided, all tenants are affected.
            wait_for_completion: Whether to poll the index status until the rebuild is done. By
                default False. Because a rebuild does not change the index configuration it has no
                observable end-state, so this wait is best-effort: it returns once the index has
                reported ready.
            timeout: When `wait_for_completion=True`, the maximum number of seconds to wait. `None`
                (the default) waits while the task keeps progressing; a stalled or vanished task is
                bounded by an internal no-progress guard, after which `ReindexTimeoutError` is raised.

        Returns:
            A `InvertedIndexTask` when `wait_for_completion=False`, or the final `InvertedIndexStatus`
            of the index when `wait_for_completion=True`.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
            weaviate.exceptions.ReindexFailedError: If `wait_for_completion=True` and the reindexing task failed.
            weaviate.exceptions.ReindexCanceledError: If `wait_for_completion=True` and the reindexing task was cancelled.
            weaviate.exceptions.ReindexTimeoutError: If `wait_for_completion=True` and `timeout` is exceeded.
        """
        self.__check_property_reindex_support("Collection config rebuild_property_index")
        index = cast(
            IndexName,
            index_name.value if isinstance(index_name, InvertedIndexType) else index_name,
        )
        return self.__submit_property_index_task(
            property_name=property_name,
            index_name=index,
            path_suffix="/rebuild",
            http_method="POST",
            body={},
            tenants=tenants,
            wait_for_completion=wait_for_completion,
            timeout=timeout,
            error_verb="rebuilt",
            error_label="Rebuild property index",
            ok_in=[202],
        )

    def cancel_property_index_task(
        self,
        property_name: str,
        index_name: InvertedIndexType,
    ) -> executor.Result[InvertedIndexTask]:
        """Cancel the live reindexing task of a property index.

        This operation is idempotent: if there is no live task for the index, the returned task
        reports a `NO_OP` status. Note that a coupled tokenization change (a `searchable` change on a
        property that also has a `filterable` index) is a single task; cancelling it via either index
        type cancels the whole task.

        Args:
            property_name: The property whose reindexing task to cancel.
            index_name: The type of the index, an `InvertedIndexType` value.

        Returns:
            A `InvertedIndexTask` with status `CANCELLED` if a live task was cancelled or `NO_OP` otherwise.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If the input parameters are invalid.
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        self.__check_property_reindex_support("Collection config cancel_property_index_task")
        index = cast(
            IndexName,
            index_name.value if isinstance(index_name, InvertedIndexType) else index_name,
        )
        _validate_input(
            [_ValidateArgument(expected=[str], name="property_name", value=property_name)]
        )
        _validate_input([_ValidateArgument(expected=[str], name="index_name", value=index)])

        path = self.__property_index_path(property_name, index) + "/cancel"

        def resp(res: Response) -> InvertedIndexTask:
            response = _decode_json_response_dict(res, "Cancel property index task")
            assert response is not None
            return _inverted_index_task_from_json(response)

        # Cancel is always 202 in merged core: CANCELLED when a live task was stopped, NO_OP otherwise.
        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=path,
            weaviate_object={},
            error_msg="Property index task may not have been cancelled.",
            status_codes=_ExpectedStatusCodes(ok_in=[202], error="Cancel property index task"),
        )

    def get_property_indexes(self) -> executor.Result[CollectionInvertedIndexes]:
        """Get the statuses of the property indexes of this collection.

        The response includes the state of any in-flight reindexing tasks, e.g. their progress and
        target configuration. Poll this endpoint for a `ready` status to detect the completion of a
        reindexing task.

        Returns:
            A `CollectionInvertedIndexes` object containing the index statuses grouped by property.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        self.__check_property_reindex_support("Collection config get_property_indexes")

        def resp(res: Response) -> CollectionInvertedIndexes:
            response = _decode_json_response_dict(res, "Get property indexes")
            assert response is not None
            return _collection_inverted_indexes_from_json(response)

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=f"/schema/{_capitalize_first_letter(self._name)}/indexes",
            error_msg="Property index statuses could not be retrieved.",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get property indexes"),
        )
