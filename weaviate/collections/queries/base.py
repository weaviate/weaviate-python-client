import datetime
import io
import pathlib
import struct
import uuid as uuid_lib
from typing import Any, Dict, Generic, List, Optional, Type, Union, cast

from google.protobuf import struct_pb2
from google.protobuf.internal.containers import RepeatedCompositeFieldContainer
from requests.exceptions import ConnectionError as RequestsConnectionError
from typing_extensions import is_typeddict

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.grpc import (
    FromReference,
    MetadataQuery,
    _MetadataQuery,
    FromNested,
    METADATA,
    PROPERTIES,
    REFERENCES,
)
from weaviate.collections.classes.internal import (
    _GroupByObject,
    _MetadataReturn,
    _GenerativeObject,
    _Object,
    _extract_properties_from_data_model,
    _extract_references_from_data_model,
    _GenerativeReturn,
    _GroupByResult,
    _GroupByReturn,
    _QueryReturn,
    _QueryOptions,
    ReturnProperties,
    ReturnReferences,
    References,
    TReferences,
    CrossReferences,
    _CrossReference,
)
from weaviate.collections.classes.types import (
    GeoCoordinate,
    Properties,
    TProperties,
)
from weaviate.collections.grpc.query import _QueryGRPC, GroupByResult, SearchResponse
from weaviate.connect import Connection
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
)
from weaviate.exceptions import WeaviateGrpcUnavailable, WeaviateQueryException
from weaviate.proto.v1 import base_pb2, search_get_pb2, properties_pb2
from weaviate.types import UUID
from weaviate.util import (
    file_encoder_b64,
    _datetime_from_weaviate_str,
    _decode_json_response_dict,
)


class _WeaviateUUIDInt(uuid_lib.UUID):
    def __init__(self, hex_: int) -> None:
        object.__setattr__(self, "int", hex_)


class _BaseQuery(Generic[Properties, References]):
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        properties: Optional[Type[Properties]],
        references: Optional[Type[References]],
    ):
        self.__connection = connection
        self._name = name
        self.__tenant = tenant
        self.__consistency_level = consistency_level
        self._properties = properties
        self._references = references
        self._is_weaviate_version_123: bool = connection._weaviate_version.is_at_least(1, 23, 0)
        self.__has_reranking: bool = connection._weaviate_version.is_at_least(1, 23, 1)

    def _query(self) -> _QueryGRPC:
        if not self.__connection._grpc_available:  # type: ignore[unused-ignore,has-type] # very strange "cannot determine type of" error here when running mypy ./integration
            raise WeaviateGrpcUnavailable()
        return _QueryGRPC(
            self.__connection,
            self._name,
            self.__tenant,
            self.__consistency_level,
            is_weaviate_version_123=self._is_weaviate_version_123,
            has_reranking=self.__has_reranking,
        )

    def __extract_metadata_for_object(
        self,
        add_props: "search_get_pb2.MetadataResult",
    ) -> _MetadataReturn:
        meta = _MetadataReturn(
            distance=add_props.distance if add_props.distance_present else None,
            certainty=add_props.certainty if add_props.certainty_present else None,
            creation_time=datetime.datetime.fromtimestamp(
                add_props.creation_time_unix / 1000, tz=datetime.timezone.utc
            )
            if add_props.creation_time_unix_present
            else None,
            last_update_time=datetime.datetime.fromtimestamp(
                add_props.last_update_time_unix / 1000, tz=datetime.timezone.utc
            )
            if add_props.last_update_time_unix_present
            else None,
            score=add_props.score if add_props.score_present else None,
            explain_score=add_props.explain_score if add_props.explain_score_present else None,
            is_consistent=add_props.is_consistent if add_props.is_consistent_present else None,
            rerank_score=add_props.rerank_score if add_props.rerank_score_present else None,
        )
        return meta

    def __extract_id_for_object(
        self,
        add_props: "search_get_pb2.MetadataResult",
    ) -> uuid_lib.UUID:
        if len(add_props.id_as_bytes) > 0:
            return _WeaviateUUIDInt(int.from_bytes(add_props.id_as_bytes, byteorder="big"))

        if len(add_props.id) == 0:
            raise WeaviateQueryException("The query returned an object with an empty ID string")
        return uuid_lib.UUID(add_props.id)

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
        if value.HasField("geo_value"):
            return GeoCoordinate(
                latitude=value.geo_value.latitude, longitude=value.geo_value.longitude
            )
        if value.HasField("blob_value"):
            return value.blob_value
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
    ) -> Optional[dict]:
        if len(properties) == 0:
            return None
        return {
            ref_prop.prop_name: _CrossReference._from(
                [
                    self.__result_to_query_object(
                        prop, prop.metadata, _QueryOptions(True, True, True, True, False)
                    )
                    for prop in ref_prop.properties
                ]
            )
            for ref_prop in properties
        }

    def __deserialize_primitive_122(self, value: Any) -> Any:
        if isinstance(value, str) and len(value) > 0:
            try:
                return uuid_lib.UUID(value)
            except ValueError:
                pass
            try:
                return _datetime_from_weaviate_str(value)
            except ValueError:
                pass
        if isinstance(value, list):
            return [self.__deserialize_primitive_122(val) for val in value]
        if isinstance(value, struct_pb2.Struct):
            raise ValueError(
                f"The query returned an object value where it expected a primitive. Have you missed a NestedProperty specification in your query? {value}"
            )
        return value

    def __parse_nonref_properties_result_122(
        self,
        properties: Union[search_get_pb2.PropertiesResult, base_pb2.ObjectPropertiesValue],
    ) -> dict:
        result: dict = {}

        for name, non_ref_prop in properties.non_ref_properties.items():
            result[name] = self.__deserialize_primitive_122(non_ref_prop)

        for number_array_property in properties.number_array_properties:
            result[number_array_property.prop_name] = [
                float(val) for val in number_array_property.values
            ]

        for int_array_property in properties.int_array_properties:
            result[int_array_property.prop_name] = [int(val) for val in int_array_property.values]

        for text_array_property in properties.text_array_properties:
            result[text_array_property.prop_name] = [
                self.__deserialize_primitive_122(val) for val in text_array_property.values
            ]

        for boolean_array_property in properties.boolean_array_properties:
            result[boolean_array_property.prop_name] = [
                bool(val) for val in boolean_array_property.values
            ]

        for object_property in properties.object_properties:
            result[object_property.prop_name] = self.__parse_nonref_properties_result_122(
                object_property.value,
            )

        for object_array_property in properties.object_array_properties:
            result[object_array_property.prop_name] = [
                self.__parse_nonref_properties_result_122(
                    object_property,
                )
                for object_property in object_array_property.values
            ]

        return result

    def __parse_ref_properties_result_122(
        self, properties: search_get_pb2.PropertiesResult
    ) -> Optional[dict]:
        if len(properties.ref_props) == 0:
            return None
        return {
            ref_prop.prop_name: _CrossReference._from(
                [
                    self.__result_to_query_object(
                        prop, prop.metadata, _QueryOptions(True, True, True, True, False)
                    )
                    for prop in ref_prop.properties
                ]
            )
            for ref_prop in properties.ref_props
        }

    def __result_to_query_object(
        self,
        props: search_get_pb2.PropertiesResult,
        meta: search_get_pb2.MetadataResult,
        options: _QueryOptions,
    ) -> _Object[Any, Any]:
        return _Object(
            properties=(
                self.__parse_nonref_properties_result(props.non_ref_props)
                if self._is_weaviate_version_123
                else self.__parse_nonref_properties_result_122(props)
            )
            if options.include_properties
            else {},
            metadata=self.__extract_metadata_for_object(meta)
            if options.include_metadata
            else _MetadataReturn(),
            references=(
                self.__parse_ref_properties_result(props.ref_props)
                if self._is_weaviate_version_123
                else self.__parse_ref_properties_result_122(props)
            )
            if options.include_references
            else None,
            uuid=self.__extract_id_for_object(meta),
            vector=self.__extract_vector_for_object(meta) if options.include_vector else None,
        )

    def __result_to_generative_object(
        self,
        props: search_get_pb2.PropertiesResult,
        meta: search_get_pb2.MetadataResult,
        options: _QueryOptions,
    ) -> _GenerativeObject[Any, Any]:
        return _GenerativeObject(
            properties=(
                self.__parse_nonref_properties_result(props.non_ref_props)
                if self._is_weaviate_version_123
                else self.__parse_nonref_properties_result_122(props)
            )
            if options.include_properties
            else {},
            metadata=self.__extract_metadata_for_object(meta)
            if options.include_metadata
            else _MetadataReturn(),
            references=(
                self.__parse_ref_properties_result(props.ref_props)
                if self._is_weaviate_version_123
                else self.__parse_ref_properties_result_122(props)
            )
            if options.include_references
            else None,
            uuid=self.__extract_id_for_object(meta),
            vector=self.__extract_vector_for_object(meta) if options.include_vector else None,
            generated=self.__extract_generated_for_object(meta),
        )

    def __result_to_group(
        self,
        res: GroupByResult,
        options: _QueryOptions,
    ) -> _GroupByResult[Any, Any]:
        return _GroupByResult(
            objects=[
                self.__result_to_query_object(obj.properties, obj.metadata, options)
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
        options: _QueryOptions,
        properties: Optional[
            ReturnProperties[TProperties]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
        references: Optional[
            ReturnReferences[TReferences]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
    ) -> Union[
        _QueryReturn[Properties, References],
        _QueryReturn[Properties, CrossReferences],
        _QueryReturn[Properties, TReferences],
        _QueryReturn[TProperties, References],
        _QueryReturn[TProperties, CrossReferences],
        _QueryReturn[TProperties, TReferences],
    ]:
        return _QueryReturn(
            objects=[
                self.__result_to_query_object(obj.properties, obj.metadata, options)
                for obj in res.results
            ]
        )

    def _result_to_generative_return(
        self,
        res: SearchResponse,
        options: _QueryOptions,
        properties: Optional[
            ReturnProperties[TProperties]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
        references: Optional[
            ReturnReferences[TReferences]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
    ) -> Union[
        _GenerativeReturn[Properties, References],
        _GenerativeReturn[Properties, CrossReferences],
        _GenerativeReturn[Properties, TReferences],
        _GenerativeReturn[TProperties, References],
        _GenerativeReturn[TProperties, CrossReferences],
        _GenerativeReturn[TProperties, TReferences],
    ]:
        return _GenerativeReturn(
            objects=[
                self.__result_to_generative_object(obj.properties, obj.metadata, options)
                for obj in res.results
            ],
            generated=res.generative_grouped_result
            if res.generative_grouped_result != ""
            else None,
        )

    def _result_to_groupby_return(
        self,
        res: SearchResponse,
        options: _QueryOptions,
        properties: Optional[
            ReturnProperties[TProperties]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
        references: Optional[
            ReturnReferences[TReferences]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
    ) -> Union[
        _GroupByReturn[Properties, References],
        _GroupByReturn[Properties, CrossReferences],
        _GroupByReturn[Properties, TReferences],
        _GroupByReturn[TProperties, References],
        _GroupByReturn[TProperties, CrossReferences],
        _GroupByReturn[TProperties, TReferences],
    ]:
        groups = {
            group.name: self.__result_to_group(group, options) for group in res.group_by_results
        }
        objects_group_by: List[_GroupByObject] = [
            _GroupByObject(
                properties=obj.properties,
                references=obj.references,
                metadata=obj.metadata,
                belongs_to_group=group.name,
                uuid=obj.uuid,
                vector=obj.vector,
            )
            for group in groups.values()
            for obj in group.objects
        ]
        return_ = _GroupByReturn(objects=objects_group_by, groups=groups)
        return cast(
            Union[
                _GroupByReturn[Properties, TReferences],
                _GroupByReturn[TProperties, TReferences],
            ],
            return_,
        )

    def _result_to_query_or_groupby_return(
        self,
        res: SearchResponse,
        options: _QueryOptions,
        properties: Optional[
            ReturnProperties[TProperties]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
        references: Optional[
            ReturnReferences[TReferences]
        ],  # required until 3.12 is minimum supported version to use new generics syntax
    ) -> Union[
        _QueryReturn[Properties, References],
        _QueryReturn[Properties, CrossReferences],
        _QueryReturn[Properties, TReferences],
        _QueryReturn[TProperties, References],
        _QueryReturn[TProperties, CrossReferences],
        _QueryReturn[TProperties, TReferences],
        _GroupByReturn[Properties, References],
        _GroupByReturn[Properties, CrossReferences],
        _GroupByReturn[Properties, TReferences],
        _GroupByReturn[TProperties, References],
        _GroupByReturn[TProperties, CrossReferences],
        _GroupByReturn[TProperties, TReferences],
    ]:
        return (
            self._result_to_query_return(res, options, properties, references)
            if not options.is_group_by
            else self._result_to_groupby_return(res, options, properties, references)
        )

    def __parse_generic_properties(
        self, generic_properties: Type[TProperties]
    ) -> Optional[PROPERTIES]:
        if not is_typeddict(generic_properties):
            raise TypeError(
                f"return_properties must only be a TypedDict or PROPERTIES within this context but is {type(generic_properties)}"
            )
        return _extract_properties_from_data_model(generic_properties)

    # def __parse_properties(self, return_properties: Optional[PROPERTIES]) -> Optional[PROPERTIES]:
    #     return _PropertiesParser().parse(return_properties)

    def _parse_return_properties(
        self,
        return_properties: Optional[ReturnProperties[TProperties]],
    ) -> Optional[PROPERTIES]:
        if (
            isinstance(return_properties, list)
            or isinstance(return_properties, str)
            or isinstance(return_properties, FromNested)
            or (return_properties is None and self._properties is None)
        ):
            # return self.__parse_properties(return_properties)
            return cast(Optional[PROPERTIES], return_properties)  # is not sourced from any generic
        elif return_properties is None and self._properties is not None:
            if not is_typeddict(self._properties):
                return return_properties
            return _extract_properties_from_data_model(
                self._properties
            )  # is sourced from collection-specific generic
        else:
            print(return_properties)
            assert return_properties is not None
            if not is_typeddict(return_properties):
                raise TypeError(
                    f"return_properties must only be a TypedDict or PROPERTIES within this context but is {type(return_properties)}"
                )
            return _extract_properties_from_data_model(
                return_properties
            )  # is sourced from query-specific generic

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

    def _parse_return_references(
        self, return_references: Optional[ReturnReferences[TReferences]]
    ) -> Optional[REFERENCES]:
        if (
            isinstance(return_references, list)
            or isinstance(return_references, FromReference)
            or (return_references is None and self._references is None)
        ):
            return return_references
        elif return_references is None and self._references is not None:
            if not is_typeddict(self._references):
                return return_references
            refs = _extract_references_from_data_model(self._references)
            return refs
        else:
            assert return_references is not None
            return _extract_references_from_data_model(return_references)

    @staticmethod
    def _parse_media(media: Union[str, pathlib.Path, io.BufferedReader]) -> str:
        if isinstance(media, str):  # if already encoded by user
            return media
        else:
            return file_encoder_b64(media)

    def _get_by_id_rest(
        self, name: str, uuid: UUID, include_vector: bool
    ) -> Optional[Dict[str, Any]]:
        path = f"/objects/{name}/{uuid}"
        params: Dict[str, Any] = {}
        if include_vector:
            params["include"] = "vector"
        return self.__get_from_weaviate(params=self.__apply_context(params), path=path)

    def __get_from_weaviate(self, params: Dict[str, Any], path: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.__connection.get(path=path, params=params)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Could not get object/s.") from conn_err
        if response.status_code == 200:
            response_json = _decode_json_response_dict(response, "get")
            assert response_json is not None
            return response_json
        if response.status_code == 404:
            return None
        raise UnexpectedStatusCodeException("Get object/s", response)

    def __apply_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self.__tenant is not None:
            params["tenant"] = self.__tenant
        if self.__consistency_level is not None:
            params["consistency_level"] = self.__consistency_level
        return params


# TODO: refactor PropertiesParser to handle new schema for specifying query parameters
# e.g. return_metadata, return_properties, return_references and include_vector

# class _PropertiesParser:
#     def __init__(self) -> None:
#         self.__from_references_by_prop_name: Dict[str, FromReference] = {}
#         self.__non_ref_properties: List[str] = []

#     def parse(self, properties: Optional[PROPERTIES]) -> Optional[PROPERTIES]:
#         if (
#             properties is None
#             or isinstance(properties, str)
#             or isinstance(properties, FromReference)
#             or isinstance(properties, FromNested)
#         ):
#             if isinstance(properties, str) and properties.startswith("__"):
#                 self.__parse_reference_property_string(properties)
#                 # if the user has not specified any return metadata for a reference, we want to return all
#                 from_references: List[FromReference] = []
#                 for ref in self.__from_references_by_prop_name.values():
#                     if ref.return_metadata is None:
#                         ref.return_metadata = MetadataQuery._full()
#                     from_references.append(ref)
#                 return cast(PROPERTIES, from_references)
#             else:
#                 return properties
#         elif isinstance(properties, list):
#             for prop in properties:
#                 if prop is None:
#                     continue
#                 if isinstance(prop, str):
#                     if prop.startswith("__"):
#                         self.__parse_reference_property_string(prop)
#                     else:
#                         self.__non_ref_properties.append(prop)
#                 elif isinstance(prop, FromReference):
#                     self.__from_references_by_prop_name[prop.link_on] = prop
#             # if the user has not specified any return metadata for a reference, we want to return all
#             from_references = []
#             for ref in self.__from_references_by_prop_name.values():
#                 if ref.return_metadata is None:
#                     ref.return_metadata = MetadataQuery._full()
#                 from_references.append(ref)
#             return [*self.__non_ref_properties, *from_references]
#         else:
#             raise TypeError(
#                 f"return_properties must be a list of strings and/or FromReferences, a string, or a FromReference but is {type(properties)}"
#             )

#     def __parse_reference_property_string_without_options(self, ref_prop: str) -> None:
#         match = re.search(r"__([^_]+)", ref_prop)
#         if match is None:
#             raise ValueError(
#                 f"return reference property {ref_prop} must be in the format __{{prop_name}} or __{{prop_name}}__{{properties|metadata}}_{{nested_prop_name}} when using string syntax"
#             )
#         else:
#             prop_name = match.group(1)
#             existing_from_reference = self.__from_references_by_prop_name.get(prop_name)
#             if existing_from_reference is None:
#                 self.__from_references_by_prop_name[prop_name] = FromReference(
#                     link_on=prop_name, return_properties=None, return_metadata=None
#                 )

#     def __parse_reference_property_string(self, ref_prop: str) -> None:
#         match_ = re.search(r"__([^_]+)__([^_]+)__([\w_]+)", ref_prop)
#         if match_ is None:
#             self.__parse_reference_property_string_without_options(ref_prop)
#             return

#         prop_name = match_.group(1)
#         existing_from_reference = self.__from_references_by_prop_name.get(prop_name)
#         properties_or_metadata = match_.group(2)
#         if properties_or_metadata not in ["properties", "metadata"]:
#             raise ValueError(
#                 f"return reference property {ref_prop} must be in the format __{{prop_name}} or __{{prop_name}}__{{properties|metadata}}_{{nested_prop_name}} when using string syntax"
#             )
#         nested_prop_name = match_.group(3)
#         if existing_from_reference is None:
#             self.__from_references_by_prop_name[prop_name] = FromReference(
#                 link_on=prop_name,
#                 return_properties=[nested_prop_name]
#                 if properties_or_metadata == "properties"
#                 else None,
#                 return_metadata=MetadataQuery(**{nested_prop_name: True})
#                 if properties_or_metadata == "metadata"
#                 else None,
#             )
#         else:
#             if properties_or_metadata == "properties":
#                 if existing_from_reference.return_properties is None:
#                     self.__from_references_by_prop_name[prop_name].return_properties = [
#                         nested_prop_name
#                     ]
#                 else:
#                     assert isinstance(existing_from_reference.return_properties, list)
#                     existing_from_reference.return_properties.append(nested_prop_name)
#             else:
#                 if existing_from_reference.return_metadata is None:
#                     metadata = MetadataQuery()
#                 else:
#                     metadata = existing_from_reference.return_metadata
#                 setattr(metadata, nested_prop_name, True)
#                 self.__from_references_by_prop_name[prop_name].return_metadata = metadata
