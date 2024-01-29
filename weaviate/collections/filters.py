import uuid as uuid_lib
from typing import Any, Dict, List, Literal, Optional, cast, overload

from weaviate.collections.classes.filters import (
    _CountRef,
    _MultiTargetRef,
    _SingleTargetRef,
    _Filters,
    _FilterAnd,
    _FilterOr,
    _FilterValue,
    _GeoCoordinateFilter,
    FilterValues,
    _FilterTargets,
)
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import base_pb2
from weaviate.types import TIME
from weaviate.util import _datetime_to_string


class _FilterToGRPC:
    @overload
    @staticmethod
    def convert(weav_filter: Literal[None]) -> None:
        ...

    @overload
    @staticmethod
    def convert(weav_filter: _Filters) -> base_pb2.Filters:
        ...

    @staticmethod
    def convert(weav_filter: Optional[_Filters]) -> Optional[base_pb2.Filters]:
        if weav_filter is None:
            return None
        elif isinstance(weav_filter, _FilterValue):
            return _FilterToGRPC.__value_filter(weav_filter)
        else:
            return _FilterToGRPC.__and_or_filter(weav_filter)

    @staticmethod
    def __value_filter(weav_filter: _FilterValue) -> base_pb2.Filters:
        return base_pb2.Filters(
            operator=weav_filter.operator._to_grpc(),
            value_text=_FilterToGRPC.__filter_to_text(weav_filter.value),
            value_int=weav_filter.value if isinstance(weav_filter.value, int) else None,
            value_boolean=weav_filter.value if isinstance(weav_filter.value, bool) else None,  # type: ignore
            value_number=weav_filter.value if isinstance(weav_filter.value, float) else None,
            value_int_array=_FilterToGRPC.__filter_to_int_list(weav_filter.value),
            value_number_array=_FilterToGRPC.__filter_to_float_list(weav_filter.value),
            value_text_array=_FilterToGRPC.__filter_to_text_list(weav_filter.value),
            value_boolean_array=_FilterToGRPC.__filter_to_bool_list(weav_filter.value),
            value_geo=_FilterToGRPC.__filter_to_geo(weav_filter.value),
            target=_FilterToGRPC.__to_target(weav_filter.target),
        )

    @staticmethod
    def __to_target(target: _FilterTargets) -> base_pb2.FilterTarget:
        if isinstance(target, str):
            return base_pb2.FilterTarget(property=target)
        elif isinstance(target, _CountRef):
            return base_pb2.FilterTarget(count=base_pb2.FilterReferenceCount(on=target.link_on))
        elif isinstance(target, _SingleTargetRef):
            assert target.target is not None
            return base_pb2.FilterTarget(
                single_target=base_pb2.FilterReferenceSingleTarget(
                    on=target.link_on, target=_FilterToGRPC.__to_target(target.target)
                )
            )
        else:
            assert isinstance(target, _MultiTargetRef)
            assert target.target is not None
            return base_pb2.FilterTarget(
                multi_target=base_pb2.FilterReferenceMultiTarget(
                    on=target.link_on,
                    target=_FilterToGRPC.__to_target(target.target),
                    target_collection=target.target_collection,
                )
            )

    @staticmethod
    def __filter_to_geo(value: FilterValues) -> Optional[base_pb2.GeoCoordinatesFilter]:
        if not (isinstance(value, _GeoCoordinateFilter)):
            return None

        return base_pb2.GeoCoordinatesFilter(
            latitude=value.latitude, longitude=value.longitude, distance=value.distance
        )

    @staticmethod
    def __filter_to_text(value: FilterValues) -> Optional[str]:
        if not (
            isinstance(value, TIME) or isinstance(value, str) or isinstance(value, uuid_lib.UUID)
        ):
            return None

        if isinstance(value, str):
            return value

        if isinstance(value, uuid_lib.UUID):
            return str(value)

        return _datetime_to_string(value)

    @staticmethod
    def __filter_to_text_list(value: FilterValues) -> Optional[base_pb2.TextArray]:
        if not isinstance(value, list) or not (
            isinstance(value[0], TIME)
            or isinstance(value[0], str)
            or isinstance(value[0], uuid_lib.UUID)
        ):
            return None

        if isinstance(value[0], str):
            value_list = value
        elif isinstance(value[0], uuid_lib.UUID):
            value_list = [str(uid) for uid in value]
        else:
            dates = cast(List[TIME], value)
            value_list = [_datetime_to_string(date) for date in dates]

        return base_pb2.TextArray(values=cast(List[str], value_list))

    @staticmethod
    def __filter_to_bool_list(value: FilterValues) -> Optional[base_pb2.BooleanArray]:
        if not isinstance(value, list) or not isinstance(value[0], bool):
            return None

        return base_pb2.BooleanArray(values=cast(List[bool], value))

    @staticmethod
    def __filter_to_float_list(value: FilterValues) -> Optional[base_pb2.NumberArray]:
        if not isinstance(value, list) or not isinstance(value[0], float):
            return None

        return base_pb2.NumberArray(values=cast(List[float], value))

    @staticmethod
    def __filter_to_int_list(value: FilterValues) -> Optional[base_pb2.IntArray]:
        if not isinstance(value, list) or not isinstance(value[0], int):
            return None

        return base_pb2.IntArray(values=cast(List[int], value))

    @staticmethod
    def __and_or_filter(weav_filter: _Filters) -> Optional[base_pb2.Filters]:
        assert isinstance(weav_filter, _FilterAnd) or isinstance(weav_filter, _FilterOr)
        return base_pb2.Filters(
            operator=weav_filter.operator._to_grpc(),
            filters=[
                filter_
                for single_filter in weav_filter.filters
                if (filter_ := _FilterToGRPC.convert(single_filter)) is not None
            ],
        )


class _FilterToREST:
    @staticmethod
    def convert(weav_filter: _Filters) -> Dict[str, Any]:
        if isinstance(weav_filter, _FilterValue):
            return _FilterToREST.__value_filter(weav_filter)
        else:
            return _FilterToREST.__and_or_filter(weav_filter)

    @staticmethod
    def __value_filter(weav_filter: _FilterValue) -> Dict[str, Any]:
        return {
            "operator": weav_filter.operator.value,
            "path": _FilterToREST.__to_path(weav_filter.target),
            **_FilterToREST.__parse_filter(weav_filter.value),
        }

    @staticmethod
    def __to_path(target: _FilterTargets) -> List[str]:
        if isinstance(target, str):
            return [target]
        elif isinstance(target, _SingleTargetRef):
            raise WeaviateInvalidInputError(
                "Cannot use Filter.by_ref() in the aggregate API currently. Instead use Filter.by_ref_multi_target() and specify the target collection explicitly."
            )
        else:
            assert isinstance(target, _MultiTargetRef)
            assert target.target is not None
            return [
                target.link_on,
                target.target_collection,
                *_FilterToREST.__to_path(target.target),
            ]

    @staticmethod
    def __parse_filter(value: FilterValues) -> Dict[str, Any]:
        if isinstance(value, str):
            return {"valueText": value}
        if isinstance(value, uuid_lib.UUID):
            return {"valueText": str(value)}
        if isinstance(value, TIME):
            return {"valueDate": _datetime_to_string(value)}
        if isinstance(value, bool):
            return {"valueBoolean": value}
        if isinstance(value, int):
            return {"valueInt": value}
        if isinstance(value, float):
            return {"valueNumber": value}
        if isinstance(value, list):
            if isinstance(value[0], str):
                return {"valueTextArray": value}
            if isinstance(value[0], uuid_lib.UUID):
                return {"valueTextArray": [str(val) for val in value]}
            if isinstance(value[0], TIME):
                return {"valueDateArray": [_datetime_to_string(cast(TIME, val)) for val in value]}
            if isinstance(value[0], bool):
                return {"valueBooleanArray": value}
            if isinstance(value[0], int):
                return {"valueIntArray": value}
            if isinstance(value[0], float):
                return {"valueNumberArray": value}
        raise ValueError(f"Unknown filter value type: {type(value)}")

    @staticmethod
    def __and_or_filter(weav_filter: _Filters) -> Dict[str, Any]:
        assert isinstance(weav_filter, _FilterAnd) or isinstance(weav_filter, _FilterOr)
        return {
            "operator": weav_filter.operator.value,
            "operands": [
                filter_
                for single_filter in weav_filter.filters
                if (filter_ := _FilterToREST.convert(single_filter)) is not None
            ],
        }
