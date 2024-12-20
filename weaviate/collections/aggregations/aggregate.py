import io
import json
import os
import pathlib
from typing import List, Optional, TypeVar, Union, cast

from httpx import ConnectError
from typing_extensions import ParamSpec

from weaviate.collections.classes.aggregate import (
    AProperties,
    AggregateResult,
    AggregateBoolean,
    AggregateDate,
    AggregateInteger,
    AggregateNumber,
    # AggregateReference, # Aggregate references currently bugged on Weaviate's side
    AggregateText,
    AggregateGroup,
    AggregateGroupByReturn,
    AggregateReturn,
    GroupByAggregate,
    _Metrics,
    _MetricsBoolean,
    _MetricsDate,
    _MetricsNumber,
    _MetricsInteger,
    # _MetricsReference, # Aggregate references currently bugged on Weaviate's side
    _MetricsText,
    GroupedBy,
    TopOccurrence,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import Move
from weaviate.collections.filters import _FilterToREST
from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateInvalidInputError, WeaviateQueryError
from weaviate.gql.aggregate import AggregateBuilder
from weaviate.types import NUMBER, UUID
from weaviate.util import file_encoder_b64, _decode_json_response_dict
from weaviate.validator import _ValidateArgument, _validate_input

P = ParamSpec("P")
T = TypeVar("T")


class _AggregateAsync:
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
    ):
        self._connection = connection
        self.__name = name
        self._tenant = tenant
        self._consistency_level = consistency_level

    def _query(self) -> AggregateBuilder:
        return AggregateBuilder(
            self.__name,
        )

    def _to_aggregate_result(
        self, response: dict, metrics: Optional[List[_Metrics]]
    ) -> AggregateReturn:
        try:
            result: dict = response["data"]["Aggregate"][self.__name][0]
            return AggregateReturn(
                properties=self.__parse_properties(result, metrics) if metrics is not None else {},
                total_count=result["meta"]["count"] if result.get("meta") is not None else None,
            )
        except KeyError as e:
            raise ValueError(
                f"There was an error accessing the {e} key when parsing the GraphQL response: {response}"
            )

    def _to_group_by_result(
        self, response: dict, metrics: Optional[List[_Metrics]]
    ) -> AggregateGroupByReturn:
        try:
            results: dict = response["data"]["Aggregate"][self.__name]
            return AggregateGroupByReturn(
                groups=[
                    AggregateGroup(
                        grouped_by=GroupedBy(
                            prop=result["groupedBy"]["path"][0],
                            value=result["groupedBy"]["value"],
                        ),
                        properties=(
                            self.__parse_properties(result, metrics) if metrics is not None else {}
                        ),
                        total_count=(
                            result["meta"]["count"] if result.get("meta") is not None else None
                        ),
                    )
                    for result in results
                ]
            )
        except KeyError as e:
            raise ValueError(
                f"There was an error accessing the {e} key when parsing the GraphQL response: {response}"
            )

    def __parse_properties(self, result: dict, metrics: List[_Metrics]) -> AProperties:
        props: AProperties = {}
        for metric in metrics:
            if metric.property_name in result:
                props[metric.property_name] = self.__parse_property(
                    result[metric.property_name], metric
                )
        return props

    @staticmethod
    def __parse_property(property_: dict, metric: _Metrics) -> AggregateResult:
        if isinstance(metric, _MetricsText):
            return AggregateText(
                count=property_.get("count"),
                top_occurrences=[
                    TopOccurrence(
                        count=cast(dict, top_occurrence).get("occurs"),
                        value=cast(dict, top_occurrence).get("value"),
                    )
                    for top_occurrence in property_.get("topOccurrences", [])
                ],
            )
        elif isinstance(metric, _MetricsInteger):
            return AggregateInteger(
                count=property_.get("count"),
                maximum=property_.get("maximum"),
                mean=property_.get("mean"),
                median=property_.get("median"),
                minimum=property_.get("minimum"),
                mode=property_.get("mode"),
                sum_=property_.get("sum"),
            )
        elif isinstance(metric, _MetricsNumber):
            return AggregateNumber(
                count=property_.get("count"),
                maximum=property_.get("maximum"),
                mean=property_.get("mean"),
                median=property_.get("median"),
                minimum=property_.get("minimum"),
                mode=property_.get("mode"),
                sum_=property_.get("sum"),
            )
        elif isinstance(metric, _MetricsBoolean):
            return AggregateBoolean(
                count=property_.get("count"),
                percentage_false=property_.get("percentageFalse"),
                percentage_true=property_.get("percentageTrue"),
                total_false=property_.get("totalFalse"),
                total_true=property_.get("totalTrue"),
            )
        elif isinstance(metric, _MetricsDate):
            return AggregateDate(
                count=property_.get("count"),
                maximum=property_.get("maximum"),
                median=property_.get("median"),
                minimum=property_.get("minimum"),
                mode=property_.get("mode"),
            )
        # Aggregate references currently bugged on Weaviate's side
        # elif isinstance(metric, _MetricsReference):
        #     return AggregateReference(pointing_to=property_.get("pointingTo"))
        else:
            raise ValueError(
                f"Unknown aggregation type {metric} encountered in _Aggregate.__parse_property() for property {property_}"
            )

    @staticmethod
    def _add_groupby_to_builder(
        builder: AggregateBuilder, group_by: Union[str, GroupByAggregate, None]
    ) -> AggregateBuilder:
        _validate_input(_ValidateArgument([str, GroupByAggregate, None], "group_by", group_by))
        if group_by is None:
            return builder
        if isinstance(group_by, str):
            group_by = GroupByAggregate(prop=group_by)
        builder = builder.with_group_by_filter([group_by.prop])
        if group_by.limit is not None:
            builder = builder.with_limit(group_by.limit)
        return builder.with_fields(" groupedBy { path value } ")

    def _base(
        self,
        return_metrics: Optional[List[_Metrics]],
        filters: Optional[_Filters],
        total_count: bool,
    ) -> AggregateBuilder:
        _validate_input(
            [
                _ValidateArgument([List[_Metrics], None], "return_metrics", return_metrics),
                _ValidateArgument([_Filters, None], "filters", filters),
                _ValidateArgument([bool], "total_count", total_count),
            ]
        )
        builder = self._query()
        if return_metrics is not None:
            builder = builder.with_fields(" ".join([metric.to_gql() for metric in return_metrics]))
        if filters is not None:
            builder = builder.with_where(_FilterToREST.convert(filters))
        if total_count:
            builder = builder.with_meta_count()
        if self._tenant is not None:
            builder = builder.with_tenant(self._tenant)
        return builder

    async def _do(self, query: AggregateBuilder) -> dict:
        try:
            response = await self._connection.post(
                path="/graphql", weaviate_object={"query": query.build()}
            )
        except ConnectError as conn_err:
            raise ConnectError("Query was not successful.") from conn_err

        res = _decode_json_response_dict(response, "Query was not successful")
        assert res is not None
        if (errs := res.get("errors")) is not None:
            if "Unexpected empty IN" in errs[0]["message"]:
                raise WeaviateQueryError(
                    "The query that you sent had no body so GraphQL was unable to parse it. You must provide at least one option to the aggregation method in order to build a valid query.",
                    "GQL Aggregate",
                )
            raise WeaviateQueryError(
                f"Error in GraphQL response: {json.dumps(errs, indent=2)}, for the following query: {query.build()}",
                "GQL Aggregate",
            )
        return res

    @staticmethod
    def _parse_near_options(
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        object_limit: Optional[int],
    ) -> None:
        _validate_input(
            [
                _ValidateArgument([int, float, None], "certainty", certainty),
                _ValidateArgument([int, float, None], "distance", distance),
                _ValidateArgument([int, None], "object_limit", object_limit),
            ]
        )

    @staticmethod
    def _add_hybrid_to_builder(
        builder: AggregateBuilder,
        query: Optional[str],
        alpha: Optional[NUMBER],
        vector: Optional[List[float]],
        query_properties: Optional[List[str]],
        object_limit: Optional[int],
        target_vector: Optional[str],
        max_vector_distance: Optional[NUMBER],
    ) -> AggregateBuilder:
        payload: dict = {}
        if query is not None:
            payload["query"] = query
        if alpha is not None:
            payload["alpha"] = alpha
        if vector is not None:
            payload["vector"] = vector
        if query_properties is not None:
            payload["properties"] = query_properties
        if target_vector is not None:
            payload["targetVectors"] = [target_vector]
        if max_vector_distance is not None:
            payload["maxVectorDistance"] = max_vector_distance
        builder = builder.with_hybrid(payload)
        if object_limit is not None:
            builder = builder.with_object_limit(object_limit)
        return builder

    @staticmethod
    def _add_near_image_to_builder(
        builder: AggregateBuilder,
        near_image: Union[str, pathlib.Path, io.BufferedReader],
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        object_limit: Optional[int],
        target_vector: Optional[str],
    ) -> AggregateBuilder:
        if all([certainty is None, distance is None, object_limit is None]):
            raise WeaviateInvalidInputError(
                "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
            )
        _validate_input(
            _ValidateArgument([str, pathlib.Path, io.BufferedReader], "near_image", near_image)
        )
        _AggregateAsync._parse_near_options(certainty, distance, object_limit)
        payload: dict = {}
        payload["image"] = _parse_media(near_image)
        if certainty is not None:
            payload["certainty"] = certainty
        if distance is not None:
            payload["distance"] = distance
        if target_vector is not None:
            payload["targetVector"] = target_vector
        builder = builder.with_near_image(payload, encode=False)
        if object_limit is not None:
            builder = builder.with_object_limit(object_limit)
        return builder

    @staticmethod
    def _add_near_object_to_builder(
        builder: AggregateBuilder,
        near_object: UUID,
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        object_limit: Optional[int],
        target_vector: Optional[str],
    ) -> AggregateBuilder:
        if all([certainty is None, distance is None, object_limit is None]):
            raise WeaviateInvalidInputError(
                "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
            )
        _validate_input(_ValidateArgument([UUID], "near_object", near_object))
        _AggregateAsync._parse_near_options(certainty, distance, object_limit)
        payload: dict = {}
        payload["id"] = str(near_object)
        if certainty is not None:
            payload["certainty"] = certainty
        if distance is not None:
            payload["distance"] = distance
        if target_vector is not None:
            payload["targetVector"] = target_vector
        builder = builder.with_near_object(payload)
        if object_limit is not None:
            builder = builder.with_object_limit(object_limit)
        return builder

    @staticmethod
    def _add_near_text_to_builder(
        builder: AggregateBuilder,
        query: Union[List[str], str],
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        move_to: Optional[Move],
        move_away: Optional[Move],
        object_limit: Optional[int],
        target_vector: Optional[str],
    ) -> AggregateBuilder:
        if all([certainty is None, distance is None, object_limit is None]):
            raise WeaviateInvalidInputError(
                "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
            )
        _validate_input(
            [
                _ValidateArgument([List[str], str], "query", query),
                _ValidateArgument([Move, None], "move_to", move_to),
                _ValidateArgument([Move, None], "move_away", move_away),
                _ValidateArgument([str, None], "target_vector", target_vector),
            ]
        )
        _AggregateAsync._parse_near_options(certainty, distance, object_limit)
        payload: dict = {}
        payload["concepts"] = query if isinstance(query, list) else [query]
        if certainty is not None:
            payload["certainty"] = certainty
        if distance is not None:
            payload["distance"] = distance
        if move_to is not None:
            payload["moveTo"] = move_to._to_gql_payload()
        if move_away is not None:
            payload["moveAwayFrom"] = move_away._to_gql_payload()
        if target_vector is not None:
            payload["targetVector"] = target_vector
        builder = builder.with_near_text(payload)
        if object_limit is not None:
            builder = builder.with_object_limit(object_limit)
        return builder

    @staticmethod
    def _add_near_vector_to_builder(
        builder: AggregateBuilder,
        near_vector: List[float],
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        object_limit: Optional[int],
        target_vector: Optional[str],
    ) -> AggregateBuilder:
        if all([certainty is None, distance is None, object_limit is None]):
            raise WeaviateInvalidInputError(
                "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
            )
        _validate_input(_ValidateArgument([list], "near_vector", near_vector))
        _AggregateAsync._parse_near_options(certainty, distance, object_limit)
        payload: dict = {}
        payload["vector"] = near_vector
        if certainty is not None:
            payload["certainty"] = certainty
        if distance is not None:
            payload["distance"] = distance
        if target_vector is not None:
            payload["targetVector"] = target_vector
        builder = builder.with_near_vector(payload)
        if object_limit is not None:
            builder = builder.with_object_limit(object_limit)
        return builder


def _parse_media(media: Union[str, pathlib.Path, io.BufferedReader]) -> str:
    if isinstance(media, str):  # if already encoded by user or string to path
        if os.path.isfile(media):
            return file_encoder_b64(media)
        else:
            return media
    else:
        return file_encoder_b64(media)
