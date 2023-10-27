from typing import Generic, Optional, Type, Union, cast, overload
from typing_extensions import is_typeddict

from weaviate.collections.classes.config import (
    ConsistencyLevel,
)
from weaviate.collections.classes.grpc import MetadataQuery, PROPERTIES
from weaviate.collections.classes.types import Properties, TProperties
from weaviate.collections.base import _CollectionBase
from weaviate.collections.aggregate import _AggregateCollection, _AggregateGroupByCollection
from weaviate.collections.config import _ConfigCollection
from weaviate.collections.data import _DataCollection
from weaviate.collections.query import _GenerateCollection, _GroupByCollection, _QueryCollection
from weaviate.collections.iterator import _ObjectIterator
from weaviate.collections.tenants import _Tenants
from weaviate.connect import Connection


class _Collection(_CollectionBase, Generic[Properties]):
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
        type_: Optional[Type[Properties]] = None,
    ) -> None:
        super().__init__(name)
        self._connection = connection

        self.aggregate = _AggregateCollection(self._connection, name, consistency_level, tenant)
        """This namespace includes all the querying methods available to you when using Weaviate's standard aggregation capabilities."""
        self.aggregate_group_by = _AggregateGroupByCollection(
            self._connection, name, consistency_level, tenant
        )
        """This namespace includes all the aggregate methods available to you when using Weaviate's aggregation group-by capabilities."""
        self.config = _ConfigCollection(self._connection, name)
        """This namespace includes all the CRUD methods available to you when modifying the configuration of the collection in Weaviate."""
        self.data = _DataCollection[Properties](connection, name, consistency_level, tenant, type_)
        """This namespace includes all the CUD methods available to you when modifying the data of the collection in Weaviate."""
        self.generate = _GenerateCollection(connection, name, consistency_level, tenant, type_)
        """This namespace includes all the querying methods available to you when using Weaviate's generative capabilities."""
        self.query_group_by = _GroupByCollection(connection, name, consistency_level, tenant, type_)
        """This namespace includes all the querying methods available to you when using Weaviate's querying group-by capabilities."""
        self.query = _QueryCollection[Properties](
            connection, name, self.data, consistency_level, tenant, type_
        )
        """This namespace includes all the querying methods available to you when using Weaviate's standard query capabilities."""
        self.tenants = _Tenants(connection, name)
        """This namespace includes all the CRUD methods available to you when modifying the tenants of a multi-tenancy-enabled collection in Weaviate."""

        self.__tenant = tenant
        self.__consistency_level = consistency_level
        self.__type = type_

    def with_tenant(self, tenant: Optional[str] = None) -> "_Collection":
        """Use this method to return a collection object specific to a single tenant.

        If multi-tenancy is not configured for this collection then Weaviate will throw an error.

        Arguments:
            `tenant`
                The name of the tenant to use.
        """
        return _Collection(self._connection, self.name, self.__consistency_level, tenant)

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "_Collection":
        """Use this method to return a collection object specific to a single consistency level.

        If replication is not configured for this collection then Weaviate will throw an error.

        Arguments:
            `consistency_level`
                The consistency level to use.
        """
        return _Collection(self._connection, self.name, consistency_level, self.__tenant)

    def __len__(self) -> int:
        total = self.aggregate.over_all(total_count=True).total_count
        assert total is not None
        return total

    @overload
    def iterator(
        self,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> _ObjectIterator[Properties]:
        ...

    @overload
    def iterator(
        self,
        return_metadata: Optional[MetadataQuery] = None,
        *,
        return_properties: Type[TProperties],
    ) -> _ObjectIterator[TProperties]:
        ...

    def iterator(
        self,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[TProperties]]] = None,
    ) -> Union[_ObjectIterator[Properties], _ObjectIterator[TProperties]]:
        """Use this method to return an iterator over the objects in the collection.

        This iterator keeps a record of the last object that it returned to be used in each subsequent call to
        Weaviate. Once the collection is exhausted, the iterator exits.

        If `return_metadata` and `return_properties` are not provided, all the data of each object will be
        requested from Weaviate except for its vector as this is an expensive operation. Specify `return_metadata`
        and `return_properties` to only request the data that you need.

        Arguments:
            `return_metadata`
                The metadata to return with each object.
            `return_properties`
                The properties to return with each object.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeException`
                If Weaviate reports a non-OK status.
        """
        if is_typeddict(return_properties):
            return_properties = cast(Type[TProperties], return_properties)
            return _ObjectIterator[TProperties](
                lambda limit, alpha, meta: self.query.fetch_objects(
                    limit=limit,
                    after=alpha,
                    return_metadata=meta,
                    return_properties=return_properties,
                ).objects,
                return_metadata,
                return_properties,
            )
        if return_properties is None and self.__type is not None:
            _type = cast(Type[Properties], self.__type)
            return _ObjectIterator[Properties](
                lambda limit, alpha, meta: self.query.fetch_objects(
                    limit=limit,
                    after=alpha,
                    return_metadata=meta,
                    return_properties=_type,
                ).objects,
                return_metadata,
                _type,
            )
        props = cast(PROPERTIES, return_properties)
        return _ObjectIterator[Properties](
            lambda limit, alpha, meta: self.query.fetch_objects(
                limit=limit,
                after=alpha,
                return_metadata=meta,
                return_properties=props,
            ).objects,
            return_metadata,
            props,
        )
