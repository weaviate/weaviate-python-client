import json
from dataclasses import asdict
from typing import Generic, Literal, Optional, Type, Union, overload

from weaviate.collections.aggregate import _AggregateCollection
from weaviate.collections.backups import _CollectionBackup
from weaviate.collections.base import _CollectionBase
from weaviate.collections.batch.collection import _BatchCollectionWrapper
from weaviate.collections.classes.config import (
    ConsistencyLevel,
)
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES
from weaviate.collections.classes.internal import (
    References,
    TReferences,
    ReturnProperties,
    ReturnReferences,
    CrossReferences,
)
from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.classes.types import Properties, TProperties
from weaviate.collections.config import _ConfigCollection
from weaviate.collections.data import _DataCollection
from weaviate.collections.iterator import _ObjectIterator
from weaviate.collections.query import _GenerateCollection, _QueryCollection
from weaviate.collections.tenants import _Tenants
from weaviate.connect import ConnectionV4
from weaviate.validator import _validate_input, _ValidateArgument


class Collection(_CollectionBase, Generic[Properties, References]):
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
        connection: ConnectionV4,
        name: str,
        validate_arguments: bool,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
        properties: Optional[Type[Properties]] = None,
        references: Optional[Type[References]] = None,
    ) -> None:
        super().__init__(connection, name, validate_arguments)

        self.aggregate = _AggregateCollection(
            self._connection, self.name, consistency_level, tenant
        )
        """This namespace includes all the querying methods available to you when using Weaviate's standard aggregation capabilities."""
        self.batch = _BatchCollectionWrapper[Properties](
            connection, consistency_level, self.name, tenant
        )
        """This namespace contains all the functionality to upload data in batches to Weaviate for this specific collection."""
        self.config = _ConfigCollection(self._connection, self.name, tenant)
        """This namespace includes all the CRUD methods available to you when modifying the configuration of the collection in Weaviate."""
        self.data = _DataCollection[Properties](
            connection, self.name, consistency_level, tenant, validate_arguments, properties
        )
        """This namespace includes all the CUD methods available to you when modifying the data of the collection in Weaviate."""
        self.generate = _GenerateCollection(
            connection,
            self.name,
            consistency_level,
            tenant,
            properties,
            references,
            validate_arguments,
        )
        """This namespace includes all the querying methods available to you when using Weaviate's generative capabilities."""
        self.query = _QueryCollection[Properties, References](
            connection,
            self.name,
            consistency_level,
            tenant,
            properties,
            references,
            validate_arguments,
        )
        """This namespace includes all the querying methods available to you when using Weaviate's standard query capabilities."""
        self.tenants = _Tenants(connection, self.name)
        """This namespace includes all the CRUD methods available to you when modifying the tenants of a multi-tenancy-enabled collection in Weaviate."""

        self.backup = _CollectionBackup(connection, self.name)
        """This namespace includes all the backup methods available to you when backing up a collection in Weaviate."""

        self.__tenant = tenant
        self.__consistency_level = consistency_level
        self.__properties = properties
        self.__references = references

    def with_tenant(
        self, tenant: Optional[Union[str, Tenant]] = None
    ) -> "Collection[Properties, References]":
        """Use this method to return a collection object specific to a single tenant.

        If multi-tenancy is not configured for this collection then Weaviate will throw an error.

        This method does not send a request to Weaviate. It only returns a new collection object that is specific
        to the tenant you specify.

        Arguments:
            `tenant`
                The tenant to use. Can be `str` or `wvc.tenants.Tenant`.
        """
        _validate_input(
            [_ValidateArgument(expected=[str, Tenant, None], name="tenant", value=tenant)]
        )
        return Collection[Properties, References](
            self._connection,
            self.name,
            self._validate_arguments,
            self.__consistency_level,
            tenant.name if isinstance(tenant, Tenant) else tenant,
            self.__properties,
            self.__references,
        )

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "Collection[Properties, References]":
        """Use this method to return a collection object specific to a single consistency level.

        If replication is not configured for this collection then Weaviate will throw an error.

        This method does not send a request to Weaviate. It only returns a new collection object that is specific
        to the consistency level you specify.

        Arguments:
            `consistency_level`
                The consistency level to use.
        """
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(
                        expected=[ConsistencyLevel, None],
                        name="consistency_level",
                        value=consistency_level,
                    )
                ]
            )
        return Collection[Properties, References](
            self._connection,
            self.name,
            self._validate_arguments,
            consistency_level,
            self.__tenant,
            self.__properties,
            self.__references,
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
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> _ObjectIterator[Properties, References]:
        ...

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> _ObjectIterator[Properties, CrossReferences]:
        ...

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> _ObjectIterator[Properties, TReferences]:
        ...

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> _ObjectIterator[TProperties, References]:
        ...

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> _ObjectIterator[TProperties, CrossReferences]:
        ...

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> _ObjectIterator[TProperties, TReferences]:
        ...

    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> Union[
        _ObjectIterator[Properties, References],
        _ObjectIterator[Properties, CrossReferences],
        _ObjectIterator[Properties, TReferences],
        _ObjectIterator[TProperties, References],
        _ObjectIterator[TProperties, CrossReferences],
        _ObjectIterator[TProperties, TReferences],
    ]:
        """Use this method to return an iterator over the objects in the collection.

        This iterator keeps a record of the last object that it returned to be used in each subsequent call to
        Weaviate. Once the collection is exhausted, the iterator exits.

        If `return_properties` is not provided, all the properties of each object will be
        requested from Weaviate except for its vector as this is an expensive operation. Specify `include_vector`
        to request the vector back as well. In addition, if `return_references=None` then none of the references
        are returned. Use `wvc.QueryReference` to specify which references to return.

        Arguments:
            `include_vector`
                Whether to include the vector in the metadata of the returned objects.
            `return_metadata`
                The metadata to return with each object.
            `return_properties`
                The properties to return with each object.
            `return_references`
                The references to return with each object.

        Raises:
            `weaviate.exceptions.WeaviateGRPCQueryError`:
                If the request to the Weaviate server fails.
        """
        return _ObjectIterator(  # type: ignore
            lambda limit, after: self.query.fetch_objects(  # pyright: ignore # problems with invariance of list
                limit=limit,
                after=after,
                include_vector=include_vector,
                return_metadata=return_metadata,
                return_properties=return_properties,
                return_references=return_references,
            ).objects
        )
