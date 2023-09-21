import datetime
import io
import pathlib
import sys
from typing import (
    Any,
    Dict,
    Optional,
    Union,
    Tuple,
    Type,
    cast,
)
from typing_extensions import is_typeddict

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, get_type_hints, get_origin
else:
    from typing import Annotated, get_type_hints, get_origin

import uuid as uuid_lib

from weaviate.collection.classes.config import ConsistencyLevel
from weaviate.collection.classes.grpc import (
    FromReference,
    PROPERTIES,
)
from weaviate.collection.classes.internal import (
    _GroupByObject,
    _MetadataReturn,
    _Object,
    _Reference,
    _extract_property_type_from_annotated_reference,
    _extract_property_type_from_reference,
    _extract_properties_from_data_model,
    _GenerativeReturn,
    _QueryReturn,
    _GroupByResult,
    _GroupByReturn,
)
from weaviate.collection.classes.types import (
    Properties,
)
from weaviate.collection.grpc_query import _QueryGRPC, GroupByResult, SearchResponse, SearchResult
from weaviate.connect import Connection
from weaviate.util import file_encoder_b64
from weaviate_grpc import weaviate_pb2


class _Grpc:
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
    ):
        self.__connection = connection
        self.__name = name
        self.__tenant = tenant
        self.__consistency_level = consistency_level

    def _query(self) -> _QueryGRPC:
        return _QueryGRPC(self.__connection, self.__name, self.__tenant, self.__consistency_level)

    @staticmethod
    def _extract_metadata_for_object(
        add_props: "weaviate_pb2.ResultAdditionalProps",
    ) -> _MetadataReturn:
        return _MetadataReturn(
            uuid=uuid_lib.UUID(add_props.id) if len(add_props.id) > 0 else None,
            vector=[float(num) for num in add_props.vector] if len(add_props.vector) > 0 else None,
            distance=add_props.distance if add_props.distance_present else None,
            certainty=add_props.certainty if add_props.certainty_present else None,
            creation_time_unix=add_props.creation_time_unix
            if add_props.creation_time_unix_present
            else None,
            last_update_time_unix=add_props.last_update_time_unix
            if add_props.last_update_time_unix_present
            else None,
            score=add_props.score if add_props.score_present else None,
            explain_score=add_props.explain_score if add_props.explain_score_present else None,
            is_consistent=add_props.is_consistent,
            generative=add_props.generative if add_props.generative_present else None,
        )

    def _deserialize_primitive(self, value: Any, type_value: Any) -> Any:
        if type_value == uuid_lib.UUID:
            return uuid_lib.UUID(value)
        if type_value == datetime.datetime:
            return datetime.datetime.fromisoformat(value)
        if isinstance(type_value, list):
            return [
                self._deserialize_primitive(val, type_value[idx]) for idx, val in enumerate(value)
            ]
        return value

    def __parse_result(
        self, properties: "weaviate_pb2.ResultProperties", type_: Optional[Type[Properties]]
    ) -> Properties:
        hints = get_type_hints(type_) if get_origin(type_) is not dict and type_ is not None else {}
        result = {}

        for name, non_ref_prop in properties.non_ref_properties.items():
            result[name] = self._deserialize_primitive(non_ref_prop, hints.get(name))

        for number_array_property in properties.number_array_properties:
            result[number_array_property.prop_name] = [
                float(val) for val in number_array_property.values
            ]

        for int_array_property in properties.int_array_properties:
            result[int_array_property.prop_name] = [int(val) for val in int_array_property.values]

        for text_array_property in properties.text_array_properties:
            result[text_array_property.prop_name] = [str(val) for val in text_array_property.values]

        for boolean_array_property in properties.boolean_array_properties:
            result[boolean_array_property.prop_name] = [
                bool(val) for val in boolean_array_property.values
            ]

        for ref_prop in properties.ref_props:
            hint = hints.get(ref_prop.prop_name)
            if hint is not None:
                if get_origin(hint) is Annotated:
                    referenced_property_type = _extract_property_type_from_annotated_reference(hint)
                else:
                    assert get_origin(hint) is _Reference
                    referenced_property_type = _extract_property_type_from_reference(hint)
                result[ref_prop.prop_name] = _Reference._from(
                    [
                        _Object(
                            properties=self.__parse_result(prop, referenced_property_type),
                            metadata=self._extract_metadata_for_object(prop.metadata),
                        )
                        for prop in ref_prop.properties
                    ]
                )
            else:
                result[ref_prop.prop_name] = _Reference._from(
                    [
                        _Object(
                            properties=self.__parse_result(prop, Dict[str, Any]),
                            metadata=self._extract_metadata_for_object(prop.metadata),
                        )
                        for prop in ref_prop.properties
                    ]
                )

        return cast(Properties, result)

    def __result_to_object(
        self, res: SearchResult, type_: Optional[Type[Properties]]
    ) -> _Object[Properties]:
        properties = self.__parse_result(res.properties, type_)
        metadata = self._extract_metadata_for_object(res.additional_properties)
        return _Object[Properties](properties=properties, metadata=metadata)

    def _result_to_query_return(
        self,
        res: SearchResponse,
        type_: Optional[Type[Properties]],
    ) -> _QueryReturn[Properties]:
        objects = [self.__result_to_object(obj, type_=type_) for obj in res.results]
        return _QueryReturn[Properties](objects=objects)

    def _result_to_generative_return(
        self,
        res: SearchResponse,
        type_: Optional[Type[Properties]],
    ) -> _GenerativeReturn[Properties]:
        objects = [self.__result_to_object(obj, type_=type_) for obj in res.results]
        grouped_results = (
            res.generative_grouped_result if res.generative_grouped_result != "" else None
        )
        return _GenerativeReturn[Properties](
            objects=objects,
            generated=grouped_results,
        )

    def _result_to_groupby_return(
        self,
        res: SearchResponse,
        type_: Optional[Type[Properties]],
    ) -> _GroupByReturn[Properties]:
        groups = {
            group.name: self.__result_to_group(group, type_) for group in res.group_by_results
        }

        objects_group_by = [
            _GroupByObject[Properties](
                properties=obj.properties, metadata=obj.metadata, belongs_to_group=group.name
            )
            for group in groups.values()
            for obj in group.objects
        ]

        return _GroupByReturn[Properties](objects=objects_group_by, groups=groups)

    def __result_to_group(
        self, res: GroupByResult, type_: Optional[Type[Properties]]
    ) -> _GroupByResult[Properties]:
        return _GroupByResult[Properties](
            objects=[self.__result_to_object(obj, type_) for obj in res.objects],
            name=res.name,
            number_of_objects=res.number_of_objects,
            min_distance=res.min_distance,
            max_distance=res.max_distance,
        )

    def _determine_generic(
        self, type_: Union[PROPERTIES, Type[Properties], None]
    ) -> Tuple[Optional[PROPERTIES], Type[Properties]]:
        if (
            isinstance(type_, list)
            or isinstance(type_, str)
            or isinstance(type_, FromReference)
            or type_ is None
        ):
            ret_properties = cast(Optional[PROPERTIES], type_)
            ret_type = cast(Type[Properties], Dict[str, Any])
        else:
            if not is_typeddict(type_):
                raise TypeError(
                    f"return_properties must only be a TypedDict or PROPERTIES within this context but is {type(type_)}"
                )
            type_ = cast(Type[Properties], type_)
            ret_properties = _extract_properties_from_data_model(type_)
            ret_type = type_
        return ret_properties, ret_type

    @staticmethod
    def _parse_media(media: Union[str, pathlib.Path, io.BufferedReader]) -> str:
        if isinstance(media, str):  # if already encoded by user
            return media
        else:
            return file_encoder_b64(media)
