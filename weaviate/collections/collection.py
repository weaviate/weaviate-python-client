import json
from dataclasses import asdict
from typing import Generic, Optional, Type, Union, cast, overload
from typing_extensions import is_typeddict
from weaviate.collections.backups import _CollectionBackup

from weaviate.collections.batch import _BatchCollection, BatchExecutor
from weaviate.collections.classes.config import (
    ConsistencyLevel,
)
from weaviate.collections.classes.grpc import METADATA, PROPERTIES
from weaviate.collections.classes.types import Properties, TProperties
from weaviate.collections.base import _CollectionBase
from weaviate.collections.aggregate import _AggregateCollection, _AggregateGroupByCollection
from weaviate.collections.config import _ConfigCollection
from weaviate.collections.data import _DataCollection
from weaviate.collections.query import _GenerateCollection, _GroupByCollection, _QueryCollection
from weaviate.collections.iterator import _ObjectIterator
from weaviate.collections.tenants import _Tenants
from weaviate.connect import Connection


class Collection(_CollectionBase, Generic[Properties]):
    """The collection class is the main entry point for interacting with a collection in Weaviate.

    This class is returned by the `client.collections.create` and `client.collections.get` methods. It provides
    access to all the methods available to you when interacting with a collection in Weaviate.

    You should not need to instantiate this class yourself but it may be useful to import this as a type when
    performing type hinting of functions that depend on a collection object.

    Attributes:
        `aggregate`
            This namespace includes all the querying methods available to you when using Weaviate's standard aggregation capabilities.
        `aggregate_group_by`
            This namespace includes all the aggregate methods available to you when using Weaviate's aggregation group-by capabilities.
        `config`
            This namespace includes all the CRUD methods available to you when modifying the configuration of the collection in Weaviate.
        `data`
            This namespace includes all the CUD methods available to you when modifying the data of the collection in Weaviate.
        `generate`
            This namespace includes all the querying methods available to you when using Weaviate's generative capabilities.
        `query_group_by`
            This namespace includes all the querying methods available to you when using Weaviate's querying group-by capabilities.
        `query`
            This namespace includes all the querying methods available to you when using Weaviate's standard query capabilities.
        `tenants`
            This namespace includes all the CRUD methods available to you when modifying the tenants of a multi-tenancy-enabled collection in Weaviate.
    """

    def __init__(
        self,
        connection: Connection,
        name: str,
        batch_executor: BatchExecutor,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
        type_: Optional[Type[Properties]] = None,
    ) -> None:
        super().__init__(name)
        self.__batch_executor = batch_executor
        self._connection = connection

        self.aggregate = _AggregateCollection(
            self._connection, self.name, consistency_level, tenant
        )
        """This namespace includes all the querying methods available to you when using Weaviate's standard aggregation capabilities."""
        self.aggregate_group_by = _AggregateGroupByCollection(
            self._connection, self.name, consistency_level, tenant
        )
        """This namespace includes all the aggregate methods available to you when using Weaviate's aggregation group-by capabilities."""
        self.batch = _BatchCollection[Properties](connection, self.name, batch_executor, tenant)
        """This namespace contains all the functionality to upload data in batches to Weaviate for this specific collection."""
        self.config = _ConfigCollection(self._connection, self.name, tenant)
        """This namespace includes all the CRUD methods available to you when modifying the configuration of the collection in Weaviate."""
        self.data = _DataCollection[Properties](
            connection,
            self.name,
            consistency_level,
            tenant,
            type_,
        )
        """This namespace includes all the CUD methods available to you when modifying the data of the collection in Weaviate."""
        self.generate = _GenerateCollection(connection, self.name, consistency_level, tenant, type_)
        """This namespace includes all the querying methods available to you when using Weaviate's generative capabilities."""
        self.query_group_by = _GroupByCollection(
            connection, self.name, consistency_level, tenant, type_
        )
        """This namespace includes all the querying methods available to you when using Weaviate's querying group-by capabilities."""
        self.query = _QueryCollection[Properties](
            connection, self.name, self.data, consistency_level, tenant, type_
        )
        """This namespace includes all the querying methods available to you when using Weaviate's standard query capabilities."""
        self.tenants = _Tenants(connection, self.name)
        """This namespace includes all the CRUD methods available to you when modifying the tenants of a multi-tenancy-enabled collection in Weaviate."""

        self.backup = _CollectionBackup(connection, self.name)
        """This namespace includes all the backup methods available to you when backing up a collection in Weaviate."""

        self.__tenant = tenant
        self.__consistency_level = consistency_level
        self.__type = type_

    def with_tenant(self, tenant: Optional[str] = None) -> "Collection[Properties]":
        """Use this method to return a collection object specific to a single tenant.

        If multi-tenancy is not configured for this collection then Weaviate will throw an error.

        Arguments:
            `tenant`
                The name of the tenant to use.
        """
        return Collection[Properties](
            self._connection, self.name, self.__batch_executor, self.__consistency_level, tenant
        )

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "Collection[Properties]":
        """Use this method to return a collection object specific to a single consistency level.

        If replication is not configured for this collection then Weaviate will throw an error.

        Arguments:
            `consistency_level`
                The consistency level to use.
        """
        return Collection[Properties](
            self._connection, self.name, self.__batch_executor, consistency_level, self.__tenant
        )

    def __len__(self) -> int:
        total = self.aggregate.over_all(total_count=True).total_count
        assert total is not None
        return total

    def __str__(self) -> str:
        config = self.config.get()
        json_ = json.dumps(asdict(config), indent=2)
        return f"<weaviate.Collection config={json_}>"

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> _ObjectIterator[Properties]:
        ...

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
    ) -> _ObjectIterator[TProperties]:
        ...

    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[Union[PROPERTIES, Type[TProperties]]] = None,
    ) -> Union[_ObjectIterator[Properties], _ObjectIterator[TProperties]]:
        """Use this method to return an iterator over the objects in the collection.

        This iterator keeps a record of the last object that it returned to be used in each subsequent call to
        Weaviate. Once the collection is exhausted, the iterator exits.

        If `return_properties` is not provided, all the properties of each object will be
        requested from Weaviate except for its vector as this is an expensive operation. Specify `include_vector`
        to request the vector back as well.

        Arguments:
            `return_properties`
                The properties to return with each object.
            `include_vector`
                Whether to include the vector in the metadata of the returned objects.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If the request to the Weaviate server fails.
        """
        if is_typeddict(return_properties):
            return_properties = cast(Type[TProperties], return_properties)
            return _ObjectIterator[TProperties](
                lambda limit, alpha: self.query.fetch_objects(
                    limit=limit,
                    after=alpha,
                    include_vector=include_vector,
                    return_metadata=return_metadata,
                    return_properties=return_properties,
                ).objects,
            )
        if return_properties is None and self.__type is not None:
            _type = cast(Type[Properties], self.__type)
            return _ObjectIterator[Properties](
                lambda limit, alpha: self.query.fetch_objects(
                    limit=limit,
                    after=alpha,
                    include_vector=include_vector,
                    return_metadata=return_metadata,
                    return_properties=_type,
                ).objects,
            )
        props = cast(PROPERTIES, return_properties)
        return _ObjectIterator[Properties](
            lambda limit, alpha: self.query.fetch_objects(
                limit=limit,
                after=alpha,
                include_vector=include_vector,
                return_metadata=return_metadata,
                return_properties=props,
            ).objects,
        )
