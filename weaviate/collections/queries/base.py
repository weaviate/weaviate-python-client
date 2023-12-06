import io
import pathlib
import re
import struct
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)
from typing_extensions import is_typeddict

import uuid as uuid_lib

from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.grpc import (
    FromReference,
    MetadataQuery,
    _MetadataQuery,
    FromNested,
    METADATA,
    PROPERTIES,
)
from weaviate.collections.classes.internal import (
    _GroupByObject,
    _MetadataReturn,
    _GenerativeObject,
    _Object,
    _Reference,
    _extract_properties_from_data_model,
    _GenerativeReturn,
    _GroupByResult,
    _GroupByReturn,
    _QueryReturn,
    _QueryOptions,
    GenerativeReturn,
    GroupByReturn,
    QueryReturn,
    ReturnProperties,
)
from weaviate.collections.classes.types import (
    Properties,
    TProperties,
)
from weaviate.collections.grpc.query import _QueryGRPC, GroupByResult, SearchResponse
from weaviate.connect import Connection
from weaviate.exceptions import WeaviateGrpcUnavailable, WeaviateQueryException
from weaviate.util import file_encoder_b64, parse_version_string, _datetime_from_weaviate_str
from weaviate.proto.v1 import search_get_pb2, properties_pb2

T = TypeVar("T")


class _WeaviateUUID(uuid_lib.UUID):
    def __init__(self, hex_: str) -> None:
        object.__setattr__(self, "int", int(hex_.replace("-", ""), 16))


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
        self.__support_byte_vectors = (
            parse_version_string(self.__connection.server_version) > parse_version_string("1.22")
            if self.__connection.server_version != ""
            else True
        )

    def _query(self) -> _QueryGRPC:
        if not self.__connection._grpc_available:
            raise WeaviateGrpcUnavailable()
        return _QueryGRPC(
            self.__connection,
            self.__name,
            self.__tenant,
            self.__consistency_level,
            support_byte_vectors=self.__support_byte_vectors,
        )

    def __extract_metadata_for_object(
        self,
        add_props: "search_get_pb2.MetadataResult",
    ) -> Optional[_MetadataReturn]:
        meta = _MetadataReturn(
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
            is_consistent=add_props.is_consistent if add_props.is_consistent_present else None,
        )
        return None if meta._is_empty() else meta

    def __extract_id_for_object(
        self,
        add_props: "search_get_pb2.MetadataResult",
    ) -> uuid_lib.UUID:
        if not len(add_props.id) > 0:
            raise WeaviateQueryException("The query returned an object with an empty ID string")
        return _WeaviateUUID(add_props.id)

    def __extract_vector_for_object(
        self,
        add_props: "search_get_pb2.MetadataResult",
    ) -> Optional[List[float]]:
        if len(add_props.vector_bytes) == 0 and len(add_props.vector) == 0:
            return None

        if len(add_props.vector_bytes) > 0:
            vector_bytes = struct.unpack(
                f"{len(add_props.vector_bytes)//4}f", add_props.vector_bytes
            )
            return list(vector_bytes)
        else:
            # backward compatibility
            return list(add_props.vector)

    def __extract_generated_for_object(
        self,
        add_props: "search_get_pb2.MetadataResult",
    ) -> Optional[str]:
        return add_props.generative if add_props.generative_present else None

    def __deserialize_non_ref_prop(self, value: properties_pb2.Value) -> Any:
        print(value)
        if value.HasField("uuid_value"):
            return uuid_lib.UUID(value.uuid_value)
        if value.HasField("date_value"):
            return _datetime_from_weaviate_str(value.date_value)
        if value.HasField("string_value"):
            return str(value.string_value)
        if value.HasField("int_value"):
            return int(value.int_value)
        if value.HasField("number_value"):
            return float(value.number_value)
        if value.HasField("bool_value"):
            return bool(value.bool_value)
        if value.HasField("list_value"):
            return [self.__deserialize_non_ref_prop(val) for val in value.list_value.values]
        if value.HasField("object_value"):
            return self.__parse_nonref_properties_result(value.object_value)
        return value

    def __parse_nonref_properties_result(
        self,
        properties: properties_pb2.Properties,
    ) -> dict:
        return {
            name: self.__deserialize_non_ref_prop(value)
            for name, value in properties.fields.items()
        }

    def __parse_ref_properties_result(
        self, properties: RepeatedCompositeFieldContainer[search_get_pb2.RefPropertiesResult]
    ) -> dict:
        if len(properties) == 0:
            return {}
        return {
            ref_prop.prop_name: _Reference._from(
                [
                    self.__result_to_query_object(
                        prop, prop.metadata, Dict[str, Any], _QueryOptions(True, True, True)
                    )
                    for prop in ref_prop.properties
                ]
            )
            for ref_prop in properties
        }

    def __parse_result(
        self,
        properties: search_get_pb2.PropertiesResult,
    ) -> dict:
        nonref_result = self.__parse_nonref_properties_result(properties.non_ref_props)
        ref_result = self.__parse_ref_properties_result(properties.ref_props)
        return {**nonref_result, **ref_result}

    def __result_to_query_object(
        self,
        props: search_get_pb2.PropertiesResult,
        meta: search_get_pb2.MetadataResult,
        type_: Optional[
            Type[T]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
        options: _QueryOptions,
    ) -> _Object[T]:
        return _Object[T](
            properties=cast(T, self.__parse_result(props) if options.include_properties else {}),
            metadata=self.__extract_metadata_for_object(meta) if options.include_metadata else None,
            uuid=self.__extract_id_for_object(meta),
            vector=self.__extract_vector_for_object(meta) if options.include_vector else None,
        )

    def __result_to_generative_object(
        self,
        props: search_get_pb2.PropertiesResult,
        meta: search_get_pb2.MetadataResult,
        type_: Optional[
            Type[T]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
        options: _QueryOptions,
    ) -> _GenerativeObject[T]:
        return _GenerativeObject[T](
            properties=cast(T, self.__parse_result(props) if options.include_properties else {}),
            metadata=self.__extract_metadata_for_object(meta) if options.include_metadata else None,
            uuid=self.__extract_id_for_object(meta),
            vector=self.__extract_vector_for_object(meta) if options.include_vector else None,
            generated=self.__extract_generated_for_object(meta),
        )

    def __result_to_group(
        self,
        res: GroupByResult,
        type_: Optional[
            Type[T]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
        options: _QueryOptions,
    ) -> _GroupByResult[T]:
        return _GroupByResult[T](
            objects=[
                self.__result_to_query_object(obj.properties, obj.metadata, type_, options)
                for obj in res.objects
            ],
            name=res.name,
            number_of_objects=res.number_of_objects,
            min_distance=res.min_distance,
            max_distance=res.max_distance,
        )

    def _result_to_query_return(
        self,
        res: SearchResponse,
        type_: Optional[
            ReturnProperties[TProperties]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
        options: _QueryOptions,
    ) -> QueryReturn[Properties, TProperties]:
        if is_typeddict(type_):
            type_ = cast(Type[TProperties], type_)  # we know it's a typeddict
            return _QueryReturn[TProperties](
                objects=[
                    self.__result_to_query_object(obj.properties, obj.metadata, type_, options)
                    for obj in res.results
                ]
            )
        else:
            return _QueryReturn[Properties](
                objects=[
                    self.__result_to_query_object(obj.properties, obj.metadata, self._type, options)
                    for obj in res.results
                ]
            )

    def _result_to_generative_return(
        self,
        res: SearchResponse,
        type_: Optional[
            ReturnProperties[TProperties]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
        options: _QueryOptions,
    ) -> GenerativeReturn[Properties, TProperties]:
        if is_typeddict(type_):
            type_ = cast(Type[TProperties], type_)  # we know it's a typeddict
            return _GenerativeReturn[TProperties](
                objects=[
                    self.__result_to_generative_object(obj.properties, obj.metadata, type_, options)
                    for obj in res.results
                ],
                generated=res.generative_grouped_result
                if res.generative_grouped_result != ""
                else None,
            )
        else:
            return _GenerativeReturn[Properties](
                objects=[
                    self.__result_to_generative_object(
                        obj.properties, obj.metadata, self._type, options
                    )
                    for obj in res.results
                ],
                generated=res.generative_grouped_result
                if res.generative_grouped_result != ""
                else None,
            )

    def _result_to_groupby_return(
        self,
        res: SearchResponse,
        type_: Optional[
            ReturnProperties[TProperties]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
        options: _QueryOptions,
    ) -> GroupByReturn[Properties, TProperties]:
        if is_typeddict(type_):
            type_ = cast(Type[TProperties], type_)  # we know it's a typeddict
            groups = {
                group.name: self.__result_to_group(group, type_, options)
                for group in res.group_by_results
            }
            objects_group_by = [
                _GroupByObject[TProperties](
                    properties=obj.properties,
                    metadata=obj.metadata,
                    belongs_to_group=group.name,
                    uuid=obj.uuid,
                    vector=obj.vector,
                )
                for group in groups.values()
                for obj in group.objects
            ]
            return _GroupByReturn[TProperties](objects=objects_group_by, groups=groups)
        else:
            groupss = {
                group.name: self.__result_to_group(group, self._type, options)
                for group in res.group_by_results
            }
            objects_group_byy = [
                _GroupByObject[Properties](
                    properties=obj.properties,
                    metadata=obj.metadata,
                    belongs_to_group=group.name,
                    uuid=obj.uuid,
                    vector=obj.vector,
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
    ) -> Optional[PROPERTIES]:
        if (
            isinstance(return_properties, list)
            or isinstance(return_properties, str)
            or isinstance(return_properties, FromReference)
            or isinstance(return_properties, FromNested)
            or (return_properties is None and self._type is None)
        ):
            # return self.__parse_properties(return_properties)
            return cast(Optional[PROPERTIES], return_properties)
        elif return_properties is None and self._type is not None:
            return self.__parse_generic_properties(self._type)
        else:
            assert return_properties is not None
            return self.__parse_generic_properties(return_properties)

    def _parse_return_metadata(
        self, return_metadata: Optional[METADATA], include_vector: bool
    ) -> Optional[_MetadataQuery]:
        if return_metadata is None:
            ret_md = None
        elif isinstance(return_metadata, list):
            ret_md = MetadataQuery(**{str(prop): True for prop in return_metadata})
        else:
            ret_md = return_metadata
        return _MetadataQuery.from_public(ret_md, include_vector)

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
                # if the user has not specified any return metadata for a reference, we want to return all
                from_references: List[FromReference] = []
                for ref in self.__from_references_by_prop_name.values():
                    if ref.return_metadata is None:
                        ref.return_metadata = MetadataQuery._full()
                    from_references.append(ref)
                return cast(PROPERTIES, from_references)
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
            # if the user has not specified any return metadata for a reference, we want to return all
            from_references = []
            for ref in self.__from_references_by_prop_name.values():
                if ref.return_metadata is None:
                    ref.return_metadata = MetadataQuery._full()
                from_references.append(ref)
            return [*self.__non_ref_properties, *from_references]
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
                self.__from_references_by_prop_name[prop_name] = FromReference(
                    link_on=prop_name, return_properties=None, return_metadata=None
                )

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
