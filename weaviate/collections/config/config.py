import asyncio
from typing import Dict, Any, List, Literal, Optional, Tuple, Union, cast, overload

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
from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.exceptions import (
    WeaviateInvalidInputError,
)
from weaviate.util import _decode_json_response_dict, _decode_json_response_list
from weaviate.validator import _validate_input, _ValidateArgument
from weaviate.warnings import _Warnings


class _ConfigCollectionBase:
    def __init__(self, connection: ConnectionV4, name: str, tenant: Optional[str]) -> None:
        self._connection = connection
        self._name = name
        self._tenant = tenant


class _ConfigCollectionAsync(_ConfigCollectionBase):
    async def __get(self) -> Dict[str, Any]:
        response = await self._connection.get(
            path=f"/schema/{self._name}",
            error_msg="Collection configuration could not be retrieved.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Get collection configuration"),
        )
        data = response.json()
        return cast(Dict[str, Any], data)

    @overload
    async def get(self, simple: Literal[False] = ...) -> CollectionConfig: ...

    @overload
    async def get(self, simple: Literal[True]) -> CollectionConfigSimple: ...

    @overload
    async def get(self, simple: bool = ...) -> Union[CollectionConfig, CollectionConfigSimple]: ...

    async def get(self, simple: bool = False) -> Union[CollectionConfig, CollectionConfigSimple]:
        """Get the configuration for this collection from Weaviate.

        Arguments:
            simple : If True, return a simplified version of the configuration containing only name and properties.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        _validate_input([_ValidateArgument(expected=[bool], name="simple", value=simple)])
        if simple:
            return _collection_config_simple_from_json(await self.__get())
        conf = _collection_config_from_json(await self.__get())
        return conf

    async def update(
        self,
        *,
        description: Optional[str] = None,
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
    ) -> None:
        """Update the configuration for this collection in Weaviate.

        Use the `weaviate.classes.Reconfigure` class to generate the necessary configuration objects for this method.

        Arguments:
            `description`
                A description of the collection.
            `inverted_index_config`
                Configuration for the inverted index. Use `Reconfigure.inverted_index` to generate one.
            `replication_config`
                Configuration for the replication. Use `Reconfigure.replication` to generate one.
            `reranker_config`
                Configuration for the reranker. Use `Reconfigure.replication` to generate one.
            `vector_index_config` DEPRECATED USE `vectorizer_config` INSTEAD
                Configuration for the vector index of the default single vector. Use `Reconfigure.vector_index` to generate one.
            `vectorizer_config`
                Configurations for the vector index (or indices) of your collection.
                Use `Reconfigure.vector_index` if there is only one vectorizer and `Reconfigure.NamedVectors` if you have many named vectors to generate them.
            `multi_tenancy_config`
                Configuration for multi-tenancy settings. Use `Reconfigure.multi_tenancy` to generate one.
                Only `auto_tenant_creation` is supported.

        Raises:
            `weaviate.WeaviateInvalidInputError`:
                If the input parameters are invalid.
            `weaviate.WeaviateConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`:
                If Weaviate reports a non-OK status.

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
        schema = await self.__get()
        schema = config.merge_with_existing(schema)
        await self._connection.put(
            path=f"/schema/{self._name}",
            weaviate_object=schema,
            error_msg="Collection configuration may not have been updated.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Update collection configuration"),
        )

    async def _add_property(self, additional_property: PropertyType) -> None:
        path = f"/schema/{self._name}/properties"
        obj = additional_property._to_dict()
        schema = await self.__get()
        if schema.get("moduleConfig"):
            configured_module = list(schema.get("moduleConfig", {}).keys())[0]
            modconf = {}
            if "skip_vectorization" in obj:
                modconf["skip"] = obj["skip_vectorization"]
                del obj["skip_vectorization"]

            if "vectorize_property_name" in obj:
                modconf["vectorizePropertyName"] = obj["vectorize_property_name"]
                del obj["vectorize_property_name"]

            if len(modconf) > 0:
                obj["moduleConfig"] = {configured_module: modconf}

        await self._connection.post(
            path=path,
            weaviate_object=obj,
            error_msg="Property may not have been added properly.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Add property to collection"),
        )

    async def _property_exists(self, property_name: str) -> bool:
        conf = _collection_config_simple_from_json(await self.__get())
        if len(conf.properties) == 0:
            return False
        for prop in conf.properties:
            if prop.name == property_name:
                return True
        return False

    async def _reference_exists(self, reference_name: str) -> bool:
        conf = _collection_config_simple_from_json(await self.__get())
        if len(conf.references) == 0:
            return False
        for ref in conf.references:
            if ref.name == reference_name:
                return True
        return False

    async def __get_shards(self) -> List[ShardStatus]:
        response = await self._connection.get(
            path=f"/schema/{self._name}/shards{f'?tenant={self._tenant}' if self._tenant else ''}",
            error_msg="Shard statuses could not be retrieved.",
        )
        shards = _decode_json_response_list(response, "get shards")
        assert shards is not None
        return [
            _ShardStatus(
                name=shard["name"],
                status=shard["status"],
                vector_queue_size=shard["vectorQueueSize"],
            )
            for shard in shards
        ]

    async def get_shards(self) -> List[ShardStatus]:
        """Get the statuses of the shards of this collection.

        If the collection is multi-tenancy and you did not call `.with_tenant` then you
        will receive the statuses of all the tenants within the collection. Otherwise, call
        `.with_tenant` on the collection first and you will receive only that single shard.

        Returns:
            `List[_ShardStatus]`:
                A list of objects containing the statuses of the shards.

        Raises:
            `weaviate.WeaviateConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`:
                If Weaviate reports a non-OK status.
        """
        return await self.__get_shards()

    async def update_shards(
        self,
        status: Literal["READY", "READONLY"],
        shard_names: Optional[Union[str, List[str]]] = None,
    ) -> Dict[str, ShardTypes]:
        """Update the status of one or all shards of this collection.

        Returns:
            `Dict[str, ShardTypes]`:
                All updated shards indexed by their name.

        Arguments:
            `status`:
                The new status of the shard. The available options are: 'READY' and 'READONLY'.
            `shard_name`:
                The shard name for which to update the status of the class of the shard. If None all shards are going to be updated.

        Raises:
            `weaviate.WeaviateConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`:
                If Weaviate reports a non-OK status.
        """
        if shard_names is None:
            shards_config = await self.__get_shards()
            shard_names = [shard_config.name for shard_config in shards_config]
        elif isinstance(shard_names, str):
            shard_names = [shard_names]

        results = await asyncio.gather(
            *[self.__update_shard(shard_name, status) for shard_name in shard_names]
        )

        return {result[0]: result[1] for result in results}

    async def __update_shard(self, shard_name: str, status: str) -> Tuple[str, ShardTypes]:
        path = f"/schema/{self._name}/shards/{shard_name}"
        data = {"status": status}
        response = await self._connection.put(
            path=path,
            weaviate_object=data,
            error_msg=f"shard '{shard_name}' may not have been updated.",
        )
        resp = _decode_json_response_dict(response, f"Update shard '{shard_name}' status")
        assert resp is not None
        return shard_name, resp["status"]

    async def add_property(self, prop: Property) -> None:
        """Add a property to the collection in Weaviate.

        Arguments:
            prop : The property to add to the collection.

        Raises:
            `weaviate.WeaviateConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`:
                If Weaviate reports a non-OK status.
            `weaviate.WeaviateInvalidInputError`:
                If the property already exists in the collection.
        """
        _validate_input([_ValidateArgument(expected=[Property], name="prop", value=prop)])
        if await self._property_exists(prop.name):
            raise WeaviateInvalidInputError(
                f"Property with name '{prop.name}' already exists in collection '{self._name}'."
            )
        await self._add_property(prop)

    async def add_reference(
        self, ref: Union[ReferenceProperty, _ReferencePropertyMultiTarget]
    ) -> None:
        """Add a reference to the collection in Weaviate.

        Arguments:
            ref : The reference to add to the collection.

        Raises:
            `weaviate.WeaviateConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`:
                If Weaviate reports a non-OK status.
            `weaviate.WeaviateInvalidInputError`:
                If the reference already exists in the collection.
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
        exists = await self._reference_exists(ref.name)
        if exists:
            raise WeaviateInvalidInputError(
                f"Reference with name '{ref.name}' already exists in collection '{self._name}'."
            )
        await self._add_property(ref)
