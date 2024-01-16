import uuid as uuid_lib
from typing import Any, Dict, List, Literal, Optional, cast, overload

from weaviate.collections.classes.filters import (
    _FilterValue2,
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
from weaviate.util import _ServerVersion, _datetime_to_string
from weaviate.types import TIME
from weaviate.proto.v1 import base_pb2


class _FilterToGRPC:
    @overload
    @staticmethod
    def convert(weav_filter: Literal[None], weaviate_version: _ServerVersion) -> None:
        ...

    @overload
    @staticmethod
    def convert(weav_filter: _Filters, weaviate_version: _ServerVersion) -> base_pb2.Filters:
        ...

    @staticmethod
    def convert(
        weav_filter: Optional[_Filters], weaviate_version: _ServerVersion
    ) -> Optional[base_pb2.Filters]:
        if weav_filter is None:
            return None
        if isinstance(weav_filter, _FilterValue):
            return _FilterToGRPC.__value_filter_old(weav_filter)
        elif isinstance(weav_filter, _FilterValue2):
            if weaviate_version.is_lower_than(
                major=1, minor=23, patch=3
            ):  # increase after next weaviate release
                return _FilterToGRPC.__value_filter_bc(weav_filter)
            return _FilterToGRPC.__value_filter(weav_filter)
        else:
            return _FilterToGRPC.__and_or_filter(weav_filter, weaviate_version)

    @staticmethod
    def __value_filter_old(weav_filter: _FilterValue) -> base_pb2.Filters:
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
            on=weav_filter.path if isinstance(weav_filter.path, list) else [weav_filter.path],
        )

    @staticmethod
    def __value_filter(weav_filter: _FilterValue2) -> base_pb2.Filters:
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
    def __to_target(target: Optional[_FilterTargets]) -> Optional[base_pb2.FilterTarget]:
        if target is None:
            return None
        if isinstance(target, str):
            return base_pb2.FilterTarget(property=target)
        elif isinstance(target, _SingleTargetRef):
            return base_pb2.FilterTarget(
                single_target=base_pb2.FilterReferenceSingleTarget(
                    on=target.link_on, target=_FilterToGRPC.__to_target(target.target)
                )
            )
        else:
            assert isinstance(target, _MultiTargetRef)
            return base_pb2.FilterTarget(
                multi_target=base_pb2.FilterReferenceMultiTarget(
                    on=target.link_on,
                    target=_FilterToGRPC.__to_target(target.target),
                    target_collection=target.target_collection,
                )
            )

    @staticmethod
    def __value_filter_bc(weav_filter: _FilterValue2) -> base_pb2.Filters:
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
            on=_FilterToGRPC.__to_target_bc(weav_filter.target),
        )

    @staticmethod
    def __to_target_bc(target: _FilterTargets) -> List[str]:
        if isinstance(target, str):
            return [target]
        elif isinstance(target, _SingleTargetRef):
            raise WeaviateInvalidInputError(
                "Single target references are not supported in this version of Weaviate. Please update to >=1.23.3."
            )
        else:
            assert isinstance(target, _MultiTargetRef)
            raise WeaviateInvalidInputError(
                "Multi target references are not supported in this version of Weaviate. Please update to >=1.23.3."
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
    def __and_or_filter(
        weav_filter: _Filters, weaviate_version: _ServerVersion
    ) -> Optional[base_pb2.Filters]:
        assert isinstance(weav_filter, _FilterAnd) or isinstance(weav_filter, _FilterOr)
        return base_pb2.Filters(
            operator=weav_filter.operator._to_grpc(),
            filters=[
                filter_
                for single_filter in weav_filter.filters
                if (filter_ := _FilterToGRPC.convert(single_filter, weaviate_version)) is not None
            ],
        )


class _FilterToREST:
    @overload
    @staticmethod
    def convert(weav_filter: Literal[None]) -> None:
        ...

    @overload
    @staticmethod
    def convert(weav_filter: _Filters) -> Dict[str, Any]:
        ...

    @staticmethod
    def convert(weav_filter: Optional[_Filters]) -> Optional[Dict[str, Any]]:
        if weav_filter is None:
            return None
        if isinstance(weav_filter, _FilterValue):
            return _FilterToREST.__value_filter_old(weav_filter)
        elif isinstance(weav_filter, _FilterValue2):
            return _FilterToREST.__value_filter(weav_filter)
        else:
            return _FilterToREST.__and_or_filter(weav_filter)

    @staticmethod
    def __value_filter(weav_filter: _FilterValue2) -> Dict[str, Any]:
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
                "Single target references are not supported in this version of Weaviate. Please update to >=1.23.3."
            )
        else:
            assert isinstance(target, _MultiTargetRef)
            raise WeaviateInvalidInputError(
                "Multi target references are not supported in this version of Weaviate. Please update to >=1.23.3."
            )

    @staticmethod
    def __value_filter_old(weav_filter: _FilterValue) -> Dict[str, Any]:
        return {
            "operator": weav_filter.operator.value,
            "path": weav_filter.path if isinstance(weav_filter.path, list) else [weav_filter.path],
            **_FilterToREST.__parse_filter(weav_filter.value),
        }

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
