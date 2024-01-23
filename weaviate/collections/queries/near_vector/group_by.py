from typing import Generic, List, Literal, Optional, Type, Union, overload

from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES
from weaviate.collections.classes.internal import (
    _GroupBy,
    GroupByReturn,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
    References,
    CrossReferences,
    TReferences,
)
from weaviate.collections.classes.types import (
    Properties,
    TProperties,
)
from weaviate.collections.queries.base import _BaseQuery
from weaviate.warnings import _Warnings


class _NearVectorGroupBy(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[Union[float, int]] = None,
        distance: Optional[Union[float, int]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> GroupByReturn[Properties, References]:
        ...

    @overload
    def near_vector(
        self,
        near_vector: List[float],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[Union[float, int]] = None,
        distance: Optional[Union[float, int]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> GroupByReturn[Properties, CrossReferences]:
        ...

    @overload
    def near_vector(
        self,
        near_vector: List[float],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[Union[float, int]] = None,
        distance: Optional[Union[float, int]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> GroupByReturn[Properties, TReferences]:
        ...

    @overload
    def near_vector(
        self,
        near_vector: List[float],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[Union[float, int]] = None,
        distance: Optional[Union[float, int]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> GroupByReturn[TProperties, References]:
        ...

    @overload
    def near_vector(
        self,
        near_vector: List[float],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[Union[float, int]] = None,
        distance: Optional[Union[float, int]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> GroupByReturn[TProperties, CrossReferences]:
        ...

    @overload
    def near_vector(
        self,
        near_vector: List[float],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[Union[float, int]] = None,
        distance: Optional[Union[float, int]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> GroupByReturn[TProperties, TReferences]:
        ...

    def near_vector(
        self,
        near_vector: List[float],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[Union[float, int]] = None,
        distance: Optional[Union[float, int]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> Union[
        GroupByReturn[Properties, References],
        GroupByReturn[Properties, CrossReferences],
        GroupByReturn[Properties, TReferences],
        GroupByReturn[TProperties, References],
        GroupByReturn[TProperties, CrossReferences],
        GroupByReturn[TProperties, TReferences],
    ]:
        """Group the results of a by-vector object search in this collection using a vector-based similarity search.

        See the [docs](https://weaviate.io/developers/weaviate/api/graphql/search-operators#nearobject) for a more detailed explanation.

        Arguments:
            `near_vector`
                The vector to search on, REQUIRED. This can be a base64 encoded string of the binary, a path to the file, or a file-like object.
            `group_by_property`
                The property to group by, REQUIRED.
            `number_of_groups`
                The number of groups to return, REQUIRED.
            `objects_per_group`
                The number of objects to return per group, REQUIRED.
            `certainty`
                The minimum similarity score to return. If not specified, the default certainty specified by the server is used.
            `distance`
                The maximum distance to search. If not specified, the default distance specified by the server is used.
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            `auto_limit`
                The maximum number of [autocut](https://weaviate.io/developers/weaviate/api/graphql/additional-operators#autocut) results to return. If not specified, no limit is applied.
            `filters`
                The filters to apply to the search.
            `include_vector`
                Whether to include the vector in the results. If not specified, this is set to False.
            `return_metadata`
                The metadata to return for each object, defaults to `None`.
            `return_properties`
                The properties to return for each object.
            `return_references`
                The references to return for each object.

        NOTE:
            - If `return_properties` is not provided then all properties are returned except for blob properties.
            - If `return_metadata` is not provided then no metadata is provided.
            - If `return_references` is not provided then no references are provided.

        Returns:
            A `GroupByReturn` object that includes the searched objects grouped by the specified property.

        Raises:
            `weaviate.exceptions.WeaviateGRPCQueryError`:
                If the request to the Weaviate server fails.
        """
        _Warnings.old_query_group_by_namespace("query.near_vector", "query_group_by")
        res = self._query().near_vector(
            near_vector=near_vector,
            certainty=certainty,
            distance=distance,
            filters=filters,
            group_by=_GroupBy(
                prop=group_by_property,
                number_of_groups=number_of_groups,
                objects_per_group=objects_per_group,
            ),
            limit=limit,
            autocut=auto_limit,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(return_references),
        )
        return self._result_to_groupby_return(
            res,
            _QueryOptions.from_input(
                return_metadata,
                return_properties,
                include_vector,
                self._references,
                return_references,
            ),
            return_properties,
            return_references,
        )
