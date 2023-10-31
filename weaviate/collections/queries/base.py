import datetime
import io
import pathlib
import re
import sys
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from typing_extensions import is_typeddict

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, get_type_hints, get_origin
else:
    from typing import Annotated, get_type_hints, get_origin

import uuid as uuid_lib

from google.protobuf import struct_pb2

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.grpc import (
    FromReference,
    MetadataQuery,
    FromNested,
    PROPERTIES,
)
from weaviate.collections.classes.internal import (
    _GroupByObject,
    _MetadataResult,
    _GenerativeObject,
    _Object,
    _Reference,
    _extract_property_type_from_annotated_reference,
    _extract_property_type_from_reference,
    _extract_properties_from_data_model,
    _GenerativeReturn,
    _GroupByResult,
    _GroupByReturn,
    _QueryReturn,
    GenerativeReturn,
    GroupByReturn,
    QueryReturn,
    ReturnProperties,
)
from weaviate.collections.classes.types import (
    Properties,
    TProperties,
)
from weaviate.collections.grpc.query import _QueryGRPC, GroupByResult, SearchResponse, SearchResult
from weaviate.connect import Connection
from weaviate.exceptions import WeaviateGrpcUnavailable
from weaviate.util import file_encoder_b64
from weaviate.proto.v1 import base_pb2, search_get_pb2

T = TypeVar("T")


class _Grpc(Generic[Properties]):
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        type_: Optional[Type[Properties]],
    ):
        self.__connection = connection
        self.__name = name
        self.__tenant = tenant
        self.__consistency_level = consistency_level
        self._type = type_

    def _query(self) -> _QueryGRPC:
        if not self.__connection._grpc_available:
            raise WeaviateGrpcUnavailable()
        return _QueryGRPC(self.__connection, self.__name, self.__tenant, self.__consistency_level)

    @staticmethod
    def _extract_metadata_for_object(
        add_props: "search_get_pb2.MetadataResult",
    ) -> _MetadataResult:
        return _MetadataResult(
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
        if isinstance(value, struct_pb2.Struct):
            raise ValueError(
                f"The query returned an object value where it expected a primitive. Have you missed a NestedProperty specification in your query? {value}"
            )
        return value

    def __parse_nonref_properties_result(
        self,
        properties: Union[search_get_pb2.PropertiesResult, base_pb2.ObjectPropertiesValue],
        type_: Optional[Any],
    ) -> dict:
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

        for object_property in properties.object_properties:
            result[object_property.prop_name] = self.__parse_nonref_properties_result(
                object_property.value, type_=hints.get(object_property.prop_name)
            )

        for object_array_property in properties.object_array_properties:
            result[object_array_property.prop_name] = [
                self.__parse_nonref_properties_result(
                    object_property,
                    hints.get(
                        object_array_property.prop_name,
                        [None for _ in range(len(object_array_property.values))][i],
                    ),
                )
                for i, object_property in enumerate(object_array_property.values)
            ]

        return result

    def __parse_ref_properties_result(
        self, properties: "search_get_pb2.PropertiesResult", type_: Optional[Type[T]]
    ) -> dict:
        hints = get_type_hints(type_) if get_origin(type_) is not dict and type_ is not None else {}
        result = {}
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
                            metadata=self._extract_metadata_for_object(prop.metadata)._to_return(),
                        )
                        for prop in ref_prop.properties
                    ]
                )
            else:
                result[ref_prop.prop_name] = _Reference._from(
                    [
                        _Object(
                            properties=self.__parse_result(prop, Dict[str, Any]),
                            metadata=self._extract_metadata_for_object(prop.metadata)._to_return(),
                        )
                        for prop in ref_prop.properties
                    ]
                )
        return result

    def __parse_result(
        self, properties: "search_get_pb2.PropertiesResult", type_: Optional[Type[T]]
    ) -> T:
        nonref_result = self.__parse_nonref_properties_result(properties, type_)
        ref_result = self.__parse_ref_properties_result(properties, type_)
        return cast(T, {**nonref_result, **ref_result})

    def __result_to_query_object(self, res: SearchResult, type_: Optional[Type[T]]) -> _Object[T]:
        properties = self.__parse_result(res.properties, type_)
        metadata = self._extract_metadata_for_object(res.metadata)
        return _Object[T](properties=properties, metadata=metadata._to_return())

    def __result_to_generative_object(
        self, res: SearchResult, type_: Optional[Type[T]]
    ) -> _GenerativeObject[T]:
        properties = self.__parse_result(res.properties, type_)
        metadata = self._extract_metadata_for_object(res.metadata)
        return _GenerativeObject[T](
            properties=properties, metadata=metadata._to_return(), generated=metadata.generative
        )

    def __result_to_group(self, res: GroupByResult, type_: Optional[Type[T]]) -> _GroupByResult[T]:
        return _GroupByResult[T](
            objects=[self.__result_to_query_object(obj, type_) for obj in res.objects],
            name=res.name,
            number_of_objects=res.number_of_objects,
            min_distance=res.min_distance,
            max_distance=res.max_distance,
        )

    def _result_to_query_return(
        self,
        res: SearchResponse,
        type_: Optional[ReturnProperties[TProperties]],
    ) -> QueryReturn[Properties, TProperties]:
        if is_typeddict(type_):
            type_ = cast(Type[TProperties], type_)  # we know it's a typeddict
            return _QueryReturn[TProperties](
                objects=[self.__result_to_query_object(obj, type_=type_) for obj in res.results]
            )
        else:
            return _QueryReturn[Properties](
                objects=[
                    self.__result_to_query_object(obj, type_=self._type) for obj in res.results
                ]
            )

    def _result_to_generative_return(
        self,
        res: SearchResponse,
        type_: Optional[ReturnProperties[TProperties]],
    ) -> GenerativeReturn[Properties, TProperties]:
        if is_typeddict(type_):
            type_ = cast(Type[TProperties], type_)  # we know it's a typeddict
            return _GenerativeReturn[TProperties](
                objects=[
                    self.__result_to_generative_object(obj, type_=type_) for obj in res.results
                ],
                generated=res.generative_grouped_result
                if res.generative_grouped_result != ""
                else None,
            )
        else:
            return _GenerativeReturn[Properties](
                objects=[
                    self.__result_to_generative_object(obj, type_=self._type) for obj in res.results
                ],
                generated=res.generative_grouped_result
                if res.generative_grouped_result != ""
                else None,
            )

    def _result_to_groupby_return(
        self,
        res: SearchResponse,
        type_: Optional[ReturnProperties[TProperties]],
    ) -> GroupByReturn[Properties, TProperties]:
        if is_typeddict(type_):
            type_ = cast(Type[TProperties], type_)  # we know it's a typeddict
            groups = {
                group.name: self.__result_to_group(group, type_) for group in res.group_by_results
            }
            objects_group_by = [
                _GroupByObject[TProperties](
                    properties=obj.properties, metadata=obj.metadata, belongs_to_group=group.name
                )
                for group in groups.values()
                for obj in group.objects
            ]
            return _GroupByReturn[TProperties](objects=objects_group_by, groups=groups)
        else:
            groupss = {
                group.name: self.__result_to_group(group, self._type)
                for group in res.group_by_results
            }
            objects_group_byy = [
                _GroupByObject[Properties](
                    properties=obj.properties, metadata=obj.metadata, belongs_to_group=group.name
                )
                for group in groupss.values()
                for obj in group.objects
            ]
            return _GroupByReturn[Properties](objects=objects_group_byy, groups=groupss)

    def __parse_generic_properties(
        self, generic_properties: Type[TProperties]
    ) -> Optional[PROPERTIES]:
        if not is_typeddict(generic_properties):
            raise TypeError(
                f"return_properties must only be a TypedDict or PROPERTIES within this context but is {type(generic_properties)}"
            )
        return _extract_properties_from_data_model(generic_properties)

    def __parse_properties(self, return_properties: Optional[PROPERTIES]) -> Optional[PROPERTIES]:
        return _PropertiesParser().parse(return_properties)

    def _parse_return_properties(
        self, return_properties: Optional[ReturnProperties[TProperties]]
    ) -> Tuple[Optional[PROPERTIES], Optional[MetadataQuery]]:
        if (
            isinstance(return_properties, list)
            or isinstance(return_properties, str)
            or isinstance(return_properties, FromReference)
            or isinstance(return_properties, FromNested)
            or (return_properties is None and self._type is None)
        ):
            return self.__parse_properties(return_properties), None
        elif return_properties is None and self._type is not None:
            return self.__parse_generic_properties(self._type), MetadataQuery._full()
        else:
            assert return_properties is not None
            return self.__parse_generic_properties(return_properties), None

    @staticmethod
    def _parse_media(media: Union[str, pathlib.Path, io.BufferedReader]) -> str:
        if isinstance(media, str):  # if already encoded by user
            return media
        else:
            return file_encoder_b64(media)


class _PropertiesParser:
    def __init__(self) -> None:
        self.__from_references_by_prop_name: Dict[str, FromReference] = {}
        self.__non_ref_properties: List[str] = []

    def parse(self, properties: Optional[PROPERTIES]) -> Optional[PROPERTIES]:
        if (
            properties is None
            or isinstance(properties, str)
            or isinstance(properties, FromReference)
            or isinstance(properties, FromNested)
        ):
            if isinstance(properties, str) and properties.startswith("__"):
                self.__parse_reference_property_string(properties)
                return list(self.__from_references_by_prop_name.values())
            else:
                return properties
        elif isinstance(properties, list):
            for prop in properties:
                if prop is None:
                    continue
                if isinstance(prop, str):
                    if prop.startswith("__"):
                        self.__parse_reference_property_string(prop)
                    else:
                        self.__non_ref_properties.append(prop)
                elif isinstance(prop, FromReference):
                    self.__from_references_by_prop_name[prop.link_on] = prop
            return [*self.__non_ref_properties, *self.__from_references_by_prop_name.values()]
        else:
            raise TypeError(
                f"return_properties must be a list of strings and/or FromReferences, a string, or a FromReference but is {type(properties)}"
            )

    def __parse_reference_property_string_without_options(self, ref_prop: str) -> None:
        match = re.search(r"__([^_]+)", ref_prop)
        if match is None:
            raise ValueError(
                f"return reference property {ref_prop} must be in the format __{{prop_name}} or __{{prop_name}}__{{properties|metadata}}_{{nested_prop_name}} when using string syntax"
            )
        else:
            prop_name = match.group(1)
            existing_from_reference = self.__from_references_by_prop_name.get(prop_name)
            if existing_from_reference is None:
                self.__from_references_by_prop_name[prop_name] = FromReference(link_on=prop_name)

    def __parse_reference_property_string(self, ref_prop: str) -> None:
        match_ = re.search(r"__([^_]+)__([^_]+)__([\w_]+)", ref_prop)
        if match_ is None:
            self.__parse_reference_property_string_without_options(ref_prop)
            return

        prop_name = match_.group(1)
        existing_from_reference = self.__from_references_by_prop_name.get(prop_name)
        properties_or_metadata = match_.group(2)
        if properties_or_metadata not in ["properties", "metadata"]:
            raise ValueError(
                f"return reference property {ref_prop} must be in the format __{{prop_name}} or __{{prop_name}}__{{properties|metadata}}_{{nested_prop_name}} when using string syntax"
            )
        nested_prop_name = match_.group(3)
        if existing_from_reference is None:
            self.__from_references_by_prop_name[prop_name] = FromReference(
                link_on=prop_name,
                return_properties=[nested_prop_name]
                if properties_or_metadata == "properties"
                else None,
                return_metadata=MetadataQuery(**{nested_prop_name: True})
                if properties_or_metadata == "metadata"
                else None,
            )
        else:
            if properties_or_metadata == "properties":
                if existing_from_reference.return_properties is None:
                    self.__from_references_by_prop_name[prop_name].return_properties = [
                        nested_prop_name
                    ]
                else:
                    assert isinstance(existing_from_reference.return_properties, list)
                    existing_from_reference.return_properties.append(nested_prop_name)
            else:
                if existing_from_reference.return_metadata is None:
                    metadata = MetadataQuery()
                else:
                    metadata = existing_from_reference.return_metadata
                setattr(metadata, nested_prop_name, True)
                self.__from_references_by_prop_name[prop_name].return_metadata = metadata
