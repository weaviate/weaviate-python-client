from typing import Generic, List, Optional, TypeVar, Union

from typing_extensions import ParamSpec

from weaviate.collections.classes.aggregate import (
    AggregateBoolean,
    AggregateDate,
    AggregateGroup,
    AggregateGroupByReturn,
    AggregateInteger,
    AggregateNumber,
    AggregateReference,
    AggregateResult,
    AggregateReturn,
    AggregateText,
    GroupedBy,
    TopOccurrence,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.types import GeoCoordinate
from weaviate.collections.grpc.aggregate import _AggregateGRPC
from weaviate.connect.v4 import ConnectionType
from weaviate.proto.v1 import aggregate_pb2
from weaviate.warnings import _Warnings

P = ParamSpec("P")
T = TypeVar("T")


class _BaseExecutor(Generic[ConnectionType]):
    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        validate_arguments: bool,
    ) -> None:
        self._connection = connection
        self._name = name
        self._tenant = tenant
        self._consistency_level = consistency_level
        self._grpc = _AggregateGRPC(
            weaviate_version=connection._weaviate_version,
            name=name,
            tenant=tenant,
            consistency_level=consistency_level,
            validate_arguments=validate_arguments,
        )

    def _to_result(
        self, is_groupby: bool, response: aggregate_pb2.AggregateReply
    ) -> Union[AggregateReturn, AggregateGroupByReturn]:
        if not is_groupby:
            return AggregateReturn(
                properties={
                    aggregation.property: self.__parse_property_grpc(aggregation)
                    for aggregation in response.single_result.aggregations.aggregations
                },
                total_count=response.single_result.objects_count,
            )
        if is_groupby:
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
                maximum=aggregation.int.maximum if aggregation.int.HasField("maximum") else None,
                mean=aggregation.int.mean if aggregation.int.HasField("mean") else None,
                median=aggregation.int.median if aggregation.int.HasField("median") else None,
                minimum=aggregation.int.minimum if aggregation.int.HasField("minimum") else None,
                mode=aggregation.int.mode if aggregation.int.HasField("mode") else None,
                sum_=aggregation.int.sum if aggregation.int.HasField("sum") else None,
            )
        elif aggregation.HasField("number"):
            return AggregateNumber(
                count=aggregation.number.count,
                maximum=aggregation.number.maximum
                if aggregation.number.HasField("maximum")
                else None,
                mean=aggregation.number.mean if aggregation.number.HasField("mean") else None,
                median=aggregation.number.median if aggregation.number.HasField("median") else None,
                minimum=aggregation.number.minimum
                if aggregation.number.HasField("minimum")
                else None,
                mode=aggregation.number.mode if aggregation.number.HasField("mode") else None,
                sum_=aggregation.number.sum if aggregation.number.HasField("sum") else None,
            )
        elif aggregation.HasField("boolean"):
            return AggregateBoolean(
                count=aggregation.boolean.count,
                percentage_false=aggregation.boolean.percentage_false
                if aggregation.boolean.HasField("percentage_false")
                else None,
                percentage_true=aggregation.boolean.percentage_true
                if aggregation.boolean.HasField("percentage_true")
                else None,
                total_false=aggregation.boolean.total_false
                if aggregation.boolean.HasField("total_false")
                else None,
                total_true=aggregation.boolean.total_true
                if aggregation.boolean.HasField("total_true")
                else None,
            )
        elif aggregation.HasField("date"):
            return AggregateDate(
                count=aggregation.date.count,
                maximum=aggregation.date.maximum if aggregation.date.HasField("maximum") else None,
                median=aggregation.date.median if aggregation.date.HasField("median") else None,
                minimum=aggregation.date.minimum if aggregation.date.HasField("minimum") else None,
                mode=aggregation.date.mode if aggregation.date.HasField("mode") else None,
            )
        elif aggregation.HasField("reference"):
            return AggregateReference(pointing_to=list(aggregation.reference.pointing_to))
        else:
            raise ValueError(
                f"Unknown aggregation type {aggregation} encountered in _Aggregate.__parse_property_grpc()"
            )
