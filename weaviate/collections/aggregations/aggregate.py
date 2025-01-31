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
    AggregateReference,
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
    _MetricsReference,
    _MetricsText,
    GroupedBy,
    TopOccurrence,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import Move
from weaviate.collections.classes.types import GeoCoordinate
from weaviate.collections.filters import _FilterToREST
from weaviate.collections.grpc.aggregate import _AggregateGRPC
from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateInvalidInputError, WeaviateQueryError
from weaviate.gql.aggregate import AggregateBuilder
from weaviate.proto.v1 import aggregate_pb2
from weaviate.types import NUMBER, UUID
from weaviate.util import file_encoder_b64, _decode_json_response_dict
from weaviate.validator import _ValidateArgument, _validate_input
from weaviate.warnings import _Warnings

P = ParamSpec("P")
T = TypeVar("T")


class _AggregateAsync:
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        validate_arguments: bool,
    ):
        self._connection = connection
        self.__name = name
        self._tenant = tenant
        self._consistency_level = consistency_level
        self._grpc = _AggregateGRPC(
            connection=connection,
            name=name,
            tenant=tenant,
            consistency_level=consistency_level,
            validate_arguments=validate_arguments,
        )

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

    def _to_result(
        self, response: aggregate_pb2.AggregateReply
    ) -> Union[AggregateReturn, AggregateGroupByReturn]:
        if response.HasField("single_result"):
            return AggregateReturn(
                properties={
                    aggregation.property: self.__parse_property_grpc(aggregation)
                    for aggregation in response.single_result.aggregations.aggregations
                },
                total_count=response.single_result.objects_count,
            )
        if response.HasField("grouped_results"):
            return AggregateGroupByReturn(
                groups=[
                    AggregateGroup(
                        grouped_by=self.__parse_grouped_by_value(group.grouped_by),
                        properties={
                            aggregation.property: self.__parse_property_grpc(aggregation)
                            for aggregation in group.aggregations.aggregations
                        },
                        total_count=group.objects_count,
                    )
                    for group in response.grouped_results.groups
                ]
            )
        else:
            _Warnings.unknown_type_encountered(response.WhichOneof("result"))
            return AggregateReturn(properties={}, total_count=None)

    def __parse_grouped_by_value(
        self, grouped_by: aggregate_pb2.AggregateReply.Group.GroupedBy
    ) -> GroupedBy:
        value: Union[
            str,
            int,
            float,
            bool,
            List[str],
            List[int],
            List[float],
            List[bool],
            GeoCoordinate,
            None,
        ]
        if grouped_by.HasField("text"):
            value = grouped_by.text
        elif grouped_by.HasField("int"):
            value = grouped_by.int
        elif grouped_by.HasField("number"):
            value = grouped_by.number
        elif grouped_by.HasField("boolean"):
            value = grouped_by.boolean
        elif grouped_by.HasField("texts"):
            value = list(grouped_by.texts.values)
        elif grouped_by.HasField("ints"):
            value = list(grouped_by.ints.values)
        elif grouped_by.HasField("numbers"):
            value = list(grouped_by.numbers.values)
        elif grouped_by.HasField("booleans"):
            value = list(grouped_by.booleans.values)
        elif grouped_by.HasField("geo"):
            v = grouped_by.geo
            value = GeoCoordinate(
                latitude=v.latitude,
                longitude=v.longitude,
            )
        else:
            value = None
            _Warnings.unknown_type_encountered(grouped_by.WhichOneof("value"))
        return GroupedBy(prop=grouped_by.path[0], value=value)

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
                props[metric.property_name] = self.__parse_property_gql(
                    result[metric.property_name], metric
                )
        return props

    @staticmethod
    def __parse_property_gql(property_: dict, metric: _Metrics) -> AggregateResult:
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
        elif isinstance(metric, _MetricsReference):
            return AggregateReference(pointing_to=property_.get("pointingTo"))
        else:
            raise ValueError(
                f"Unknown aggregation type {metric} encountered in _Aggregate.__parse_property() for property {property_}"
            )

    @staticmethod
    def __parse_property_grpc(
        aggregation: aggregate_pb2.AggregateReply.Aggregations.Aggregation,
    ) -> AggregateResult:
        if aggregation.HasField("text"):
            return AggregateText(
                count=aggregation.text.count,
                top_occurrences=[
                    TopOccurrence(
                        count=top_occurrence.occurs,
                        value=top_occurrence.value,
                    )
                    for top_occurrence in aggregation.text.top_occurences.items
                ],
            )
        elif aggregation.HasField("int"):
            return AggregateInteger(
                count=aggregation.int.count,
                maximum=aggregation.int.maximum,
                mean=aggregation.int.mean,
                median=aggregation.int.median,
                minimum=aggregation.int.minimum,
                mode=aggregation.int.mode,
                sum_=aggregation.int.sum,
            )
        elif aggregation.HasField("number"):
            return AggregateNumber(
                count=aggregation.number.count,
                maximum=aggregation.number.maximum,
                mean=aggregation.number.mean,
                median=aggregation.number.median,
                minimum=aggregation.number.minimum,
                mode=aggregation.number.mode,
                sum_=aggregation.number.sum,
            )
        elif aggregation.HasField("boolean"):
            return AggregateBoolean(
                count=aggregation.boolean.count,
                percentage_false=aggregation.boolean.percentage_false,
                percentage_true=aggregation.boolean.percentage_true,
                total_false=aggregation.boolean.total_false,
                total_true=aggregation.boolean.total_true,
            )
        elif aggregation.HasField("date"):
            return AggregateDate(
                count=aggregation.date.count,
                maximum=aggregation.date.maximum,
                median=aggregation.date.median,
                minimum=aggregation.date.minimum,
                mode=aggregation.date.mode,
            )
        elif aggregation.HasField("reference"):
            return AggregateReference(pointing_to=list(aggregation.reference.pointing_to))
        else:
            raise ValueError(
                f"Unknown aggregation type {aggregation} encountered in _Aggregate.__parse_property_grpc()"
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
