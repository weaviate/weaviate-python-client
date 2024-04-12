from typing import Dict, List, Literal, Optional, Union, overload

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
)

from weaviate.collections.config.asy import _ConfigCollectionAsync
from weaviate.event_loop import _EventLoop


class _ConfigCollection:
    def __init__(self, loop: _EventLoop, config: _ConfigCollectionAsync):
        self.__loop = loop
        self.__config = config

    @overload
    def get(self, simple: Literal[False] = ...) -> CollectionConfig:
        ...

    @overload
    def get(self, simple: Literal[True]) -> CollectionConfigSimple:
        ...

    @overload
    def get(self, simple: bool = ...) -> Union[CollectionConfig, CollectionConfigSimple]:
        ...

    def get(self, simple: bool = False) -> Union[CollectionConfig, CollectionConfigSimple]:
        """Get the configuration for this collection from Weaviate.

        Arguments:
            simple : If True, return a simplified version of the configuration containing only name and properties.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        return self.__loop.run_until_complete(self.__config.get, simple)

    def update(
        self,
        *,
        description: Optional[str] = None,
        inverted_index_config: Optional[_InvertedIndexConfigUpdate] = None,
        replication_config: Optional[_ReplicationConfigUpdate] = None,
        vector_index_config: Optional[
            Union[_VectorIndexConfigHNSWUpdate, _VectorIndexConfigFlatUpdate]
        ] = None,
        vectorizer_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
                List[_NamedVectorConfigUpdate],
            ]
        ] = None,
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
            `vector_index_config` DEPRECATED USE `vectorizer_config` INSTEAD
                Configuration for the vector index of the default single vector. Use `Reconfigure.vector_index` to generate one.
            `vectorizer_config`
                Configurations for the vector index (or indices) of your collection.
                Use `Reconfigure.vector_index` if there is only one vectorizer and `Reconfigure.NamedVectors` if you have many named vectors to generate them.

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
        self.__loop.run_until_complete(
            self.__config.update,
            description=description,
            inverted_index_config=inverted_index_config,
            replication_config=replication_config,
            vector_index_config=vector_index_config,
            vectorizer_config=vectorizer_config,
        )

    def get_shards(self) -> List[ShardStatus]:
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
        return self.__loop.run_until_complete(self.__config.get_shards)

    def update_shards(
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
        return self.__loop.run_until_complete(self.__config.update_shards, status, shard_names)

    def add_property(self, prop: Property) -> None:
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
        self.__loop.run_until_complete(self.__config.add_property, prop)

    def add_reference(self, ref: Union[ReferenceProperty, _ReferencePropertyMultiTarget]) -> None:
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
        self.__loop.run_until_complete(self.__config.add_reference, ref)
