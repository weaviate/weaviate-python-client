from typing import Dict, Generic, List, Literal, Optional, Union, overload

from weaviate.collections.classes.config import (
    _InvertedIndexConfigUpdate,
    _ReplicationConfigUpdate,
    _VectorIndexConfigFlatUpdate,
    Property,
    ReferenceProperty,
    _ReferencePropertyMultiTarget,
    _VectorIndexConfigHNSWUpdate,
    CollectionConfig,
    CollectionConfigSimple,
    ShardStatus,
    ShardTypes,
    _NamedVectorConfigUpdate,
    _MultiTenancyConfigUpdate,
    _GenerativeProvider,
    _RerankerProvider,
)
from weaviate.collections.classes.config_vector_index import _VectorIndexConfigDynamicUpdate
from weaviate.collections.config.executor import _ConfigExecutor
from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionType


class _ConfigCollectionBase(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType, name: str, tenant: Optional[str]) -> None:
        self._connection: ConnectionType = connection
        self._name = name
        self._tenant = tenant
        self._executor = _ConfigExecutor(connection._weaviate_version, name, tenant)


class _ConfigCollectionAsync(_ConfigCollectionBase):
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
        return await aresult(self._executor.get(simple, connection=self._connection))

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
        return await aresult(
            self._executor.update(
                connection=self._connection,
                description=description,
                inverted_index_config=inverted_index_config,
                multi_tenancy_config=multi_tenancy_config,
                replication_config=replication_config,
                vector_index_config=vector_index_config,
                vectorizer_config=vectorizer_config,
                generative_config=generative_config,
                reranker_config=reranker_config,
            )
        )

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
        return await aresult(self._executor.get_shards(connection=self._connection))

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
        return await aresult(
            self._executor.update_shards(
                status,
                shard_names,
                connection=self._connection,
            )
        )

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
        return await aresult(self._executor.add_property(prop, connection=self._connection))

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
        return await aresult(self._executor.add_reference(ref, connection=self._connection))
