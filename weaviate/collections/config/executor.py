import asyncio
from typing import Any, Dict, Generic, List, Literal, Optional, Tuple, Union, cast, overload

from httpx import Response
from pydantic_core import ValidationError

from weaviate.collections.classes.config import (
    _CollectionConfigUpdate,
    _InvertedIndexConfigUpdate,
    _ReplicationConfigUpdate,
    _VectorIndexConfigFlatUpdate,
    PropertyType,
    Property,
    ReferenceProperty,
    _ReferencePropertyMultiTarget,
    _VectorIndexConfigHNSWUpdate,
    CollectionConfig,
    CollectionConfigSimple,
    ShardStatus,
    _ShardStatus,
    ShardTypes,
    _NamedVectorConfigUpdate,
    _MultiTenancyConfigUpdate,
    _GenerativeProvider,
    _RerankerProvider,
)
from weaviate.collections.classes.config_methods import (
    _collection_config_from_json,
    _collection_config_simple_from_json,
)
from weaviate.collections.classes.config_vector_index import _VectorIndexConfigDynamicUpdate
from weaviate.connect import executor
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionAsync, ConnectionType
from weaviate.exceptions import (
    WeaviateInvalidInputError,
)
from weaviate.util import _decode_json_response_dict, _decode_json_response_list
from weaviate.validator import _validate_input, _ValidateArgument
from weaviate.warnings import _Warnings


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
        replication_config: Optional[_ReplicationConfigUpdate] = None,
        vector_index_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
            ]
        ] = None,
        vectorizer_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
                _VectorIndexConfigDynamicUpdate,
                List[_NamedVectorConfigUpdate],
            ]
        ] = None,
        generative_config: Optional[_GenerativeProvider] = None,
        reranker_config: Optional[_RerankerProvider] = None,
    ) -> executor.Result[None]:
        """Update the configuration for this collection in Weaviate.

        Use the `weaviate.classes.Reconfigure` class to generate the necessary configuration objects for this method.

        Args:
            description: A description of the collection.
            inverted_index_config: Configuration for the inverted index. Use `Reconfigure.inverted_index` to generate one.
            replication_config: Configuration for the replication. Use `Reconfigure.replication` to generate one.
            reranker_config: Configuration for the reranker. Use `Reconfigure.replication` to generate one.
            vector_index_config`: DEPRECATED USE `vectorizer_config` INSTEAD. Configuration for the vector index of the default single vector. Use `Reconfigure.vector_index` to generate one.
            vectorizer_config: Configurations for the vector index (or indices) of your collection.
                Use `Reconfigure.vector_index` if there is only one vectorizer and `Reconfigure.NamedVectors` if you have many named vectors to generate them.
            multi_tenancy_config: Configuration for multi-tenancy settings. Use `Reconfigure.multi_tenancy` to generate one.
                Only `auto_tenant_creation` is supported.

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
        try:
            config = _CollectionConfigUpdate(
                description=description,
                property_descriptions=property_descriptions,
                inverted_index_config=inverted_index_config,
                replication_config=replication_config,
                vector_index_config=vector_index_config,
                vectorizer_config=vectorizer_config,
                multi_tenancy_config=multi_tenancy_config,
                generative_config=generative_config,
                reranker_config=reranker_config,
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
                obj["vectorConfig"] = {key: modconf for key in vector_config.keys()}

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
                shard_names: Optional[Union[str, List[str]]]
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
