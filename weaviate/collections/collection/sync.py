import json
from dataclasses import asdict
from typing import Dict, Generic, List, Literal, Optional, Type, Union, overload

from weaviate.collections.aggregate import _AggregateCollection
from weaviate.collections.backups import _CollectionBackup
from weaviate.collections.batch.collection import _BatchCollectionWrapper
from weaviate.collections.classes.cluster import Shard
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES
from weaviate.collections.classes.internal import (
    CrossReferences,
    References,
    ReturnProperties,
    ReturnReferences,
    TReferences,
)
from weaviate.collections.classes.types import Properties, TProperties
from weaviate.collections.cluster import _Cluster
from weaviate.collections.config import _ConfigCollection
from weaviate.collections.data import _DataCollection
from weaviate.collections.generate import _GenerateCollection
from weaviate.collections.iterator import _IteratorInputs, _ObjectIterator
from weaviate.collections.query import _QueryCollection
from weaviate.collections.tenants import _Tenants
from weaviate.connect import ConnectionV4
from weaviate.types import UUID

from .base import _CollectionBase


class Collection(Generic[Properties, References], _CollectionBase[Properties, References]):
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
        super().__init__(
            connection,
            name,
            validate_arguments,
            consistency_level,
            tenant,
            properties,
            references,
        )

        self.__cluster = _Cluster(connection)

        config = _ConfigCollection(
            connection=connection,
            name=name,
            tenant=tenant,
        )

        self.aggregate = _AggregateCollection(
            connection=connection,
            name=name,
            consistency_level=consistency_level,
            tenant=tenant,
        )
        """This namespace includes all the querying methods available to you when using Weaviate's standard aggregation capabilities."""
        self.backup = _CollectionBackup(
            connection=connection,
            name=name,
        )
        """This namespace includes all the backup methods available to you when backing up a collection in Weaviate."""
        self.batch = _BatchCollectionWrapper[Properties](
            connection,
            consistency_level,
            name,
            tenant,
            config,
        )
        """This namespace contains all the functionality to upload data in batches to Weaviate for this specific collection."""
        self.config = config
        """This namespace includes all the CRUD methods available to you when modifying the configuration of the collection in Weaviate."""
        self.data = _DataCollection[Properties](
            connection, name, consistency_level, tenant, validate_arguments
        )
        """This namespace includes all the CUD methods available to you when modifying the data of the collection in Weaviate."""
        self.generate = _GenerateCollection[Properties, References](
            connection=connection,
            name=name,
            consistency_level=consistency_level,
            tenant=tenant,
            properties=properties,
            references=references,
            validate_arguments=validate_arguments,
        )
        """This namespace includes all the querying methods available to you when using Weaviate's generative capabilities."""
        self.query = _QueryCollection[Properties, References](
            connection=connection,
            name=name,
            consistency_level=consistency_level,
            tenant=tenant,
            properties=properties,
            references=references,
            validate_arguments=validate_arguments,
        )
        """This namespace includes all the querying methods available to you when using Weaviate's standard query capabilities."""
        self.tenants = _Tenants(
            connection=connection,
            name=name,
            consistency_level=consistency_level,
            validate_arguments=validate_arguments,
        )
        """This namespace includes all the CRUD methods available to you when modifying the tenants of a multi-tenancy-enabled collection in Weaviate."""

    def __len__(self) -> int:
        total = self.aggregate.over_all(total_count=True).total_count
        assert total is not None
        return total

    def __str__(self) -> str:
        config = self.config.get()
        json_ = json.dumps(asdict(config), indent=2)
        return f"<weaviate.Collection config={json_}>"

    def exists(self) -> bool:
        """Check if the collection exists in Weaviate."""
        try:
            self.config.get(simple=True)
            return True
        except Exception:
            return False

    def shards(self) -> List[Shard]:
        """
        Get the statuses of all the shards of this collection.

        Returns:
            The list of shards belonging to this collection.

        Raises
            `weaviate.WeaviateConnectionError`
                If the network connection to weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If weaviate reports a none OK status.
            `weaviate.EmptyResponseError`
                If the response is empty.
        """
        return [
            shard
            for node in self.__cluster.nodes(self.name, output="verbose")
            for shard in node.shards
        ]

    def _build_info(self, include_properties: bool) -> str:
        config = self.config.get()

        property_configs = config.properties

        collection_info = [
            ("Length", len(self)),
            ("Multi-tenancy", config.multi_tenancy_config.enabled),
            ("Index type", config.vector_index_type),
            ("Properties", len(property_configs)),
        ]

        DISPLAY_SPACER = "=" * 40 + "\n"
        output_str = f"{DISPLAY_SPACER}Collection summary: '{self.name}'\n{DISPLAY_SPACER}"
        for n, p in collection_info:
            output_str += f"{n}: {p}\n"

        if include_properties:
            properties_list = []
            for prop in property_configs:
                if prop.vectorizer_config is not None:
                    skip_vectorization = prop.vectorizer_config.skip
                else:
                    skip_vectorization = None

                tokenization = None if prop.tokenization is None else prop.tokenization.value

                name_col = "Property Name"

                property_info = [
                    (name_col, prop.name),
                    ("DataType", prop.data_type.value),
                    ("Tokenization", tokenization),
                    ("Skip vectorization", skip_vectorization),
                    ("Searchable", prop.index_searchable),
                    ("Filterable", prop.index_filterable),
                    ("Range filter", prop.index_range_filters),
                ]

                properties = {}
                for prop_name, prop_val in property_info:
                    properties[prop_name] = str(prop_val)
                properties_list.append(properties)

            output_str += _tabularise(properties_list)
        return output_str

    def info(self, include_properties: bool = False) -> None:
        """
        Display a summary of the collection.

        Parameters:
            include_properties (bool): Display a summary of each property
        """
        print(self._build_info(include_properties))

    def head(self, n: int = 5) -> None:
        """
        Display the first n objects from Weaviate.

        Parameters:
            n (int, default: 5): The number of objects to display
        """
        if n <= 0:
            raise ValueError(f"n of {n} entered; n must be a positive integer")

        response = self.query.fetch_objects(limit=n)

        if not response.objects or len(response.objects) == 0:
            print(f"No objects found in collection '{self.name}'")
            return

        print(f"Displaying the first {n} objects in collection '{self.name}'")
        properties_list = [o.properties for o in response.objects]
        print(_tabularise(properties_list))

    @overload
    def iterator(
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
        after: Optional[UUID] = None,
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
        after: Optional[UUID] = None,
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
        after: Optional[UUID] = None,
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
        after: Optional[UUID] = None,
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
        after: Optional[UUID] = None,
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
        after: Optional[UUID] = None,
    ) -> _ObjectIterator[TProperties, TReferences]:
        ...

    # weaviate/collections/collection.py:263: error: Overloaded function implementation does not accept all possible arguments of signature 3  [misc]
    # weaviate/collections/collection.py:263: error: Overloaded function implementation cannot produce return type of signature 3  [misc]
    def iterator(  # type: ignore
        self,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
        after: Optional[UUID] = None,
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
            `after`
                The cursor to use to mark the initial starting point of the iterator in the collection.

        Raises:
            `weaviate.exceptions.WeaviateGRPCQueryError`:
                If the request to the Weaviate server fails.
        """
        return _ObjectIterator(
            self.query,
            _IteratorInputs(
                include_vector=include_vector,
                return_metadata=return_metadata,
                return_properties=return_properties,
                return_references=return_references,
                after=after,
            ),
        )


def _tabularise(properties_list: Union[List[Dict[str, str]], List[Properties]]) -> str:
    MAX_COL_WIDTH = 20
    MIN_COL_WIDTH = 3
    SEPARATOR = " | "

    table_str = ""

    # Get all property names and their maximum lengths
    property_names = list(properties_list[0].keys())
    max_lengths = {p: len(p) for p in property_names}

    for properties in properties_list:
        for p, v in properties.items():
            max_lengths[p] = max(max_lengths[p], len(str(v)))

    # Adjust column widths
    col_widths = {
        p: min(max(len(p), min_len, MIN_COL_WIDTH), MAX_COL_WIDTH)
        for p, min_len in max_lengths.items()
    }

    # Construct the header
    header = SEPARATOR.join(p.ljust(col_widths[p]) for p in property_names) + SEPARATOR
    table_str += ("-" * len(header)) + "\n"
    table_str += header + "\n"
    table_str += ("-" * len(header)) + "\n"

    # Construct the body
    for properties in properties_list:
        row = ""
        for p in property_names:
            v = properties[p]
            if len(str(v)) <= col_widths[p]:
                row += str(v)[: col_widths[p]].ljust(col_widths[p]) + SEPARATOR
            else:
                row += str(v)[: col_widths[p] - 3] + "..." + SEPARATOR
        table_str += f"{row}\n"

    return table_str + "\n"
