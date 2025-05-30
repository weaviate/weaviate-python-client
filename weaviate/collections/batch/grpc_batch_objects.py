import datetime
import struct
import time
import uuid as uuid_package
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union, cast

from google.protobuf.struct_pb2 import Struct

from weaviate.collections.classes.batch import (
    BatchObject,
    BatchObjectReturn,
    ErrorObject,
    _BatchObject,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.internal import ReferenceInputs, ReferenceToMulti
from weaviate.collections.classes.types import GeoCoordinate, PhoneNumber
from weaviate.collections.grpc.shared import _BaseGRPC, _is_1d_vector, _Pack
from weaviate.connect import executor
from weaviate.connect.v4 import Connection
from weaviate.exceptions import (
    WeaviateInsertInvalidPropertyError,
    WeaviateInsertManyAllFailedError,
    WeaviateInvalidInputError,
)
from weaviate.proto.v1 import base_pb2, batch_pb2
from weaviate.types import VECTORS
from weaviate.util import _datetime_to_string, _ServerVersion


class _BatchGRPC(_BaseGRPC):
    """This class is used to insert multiple objects into Weaviate using the gRPC API.

    It is used within the `_Data` and `_Batch` classes hence the necessary generalities
    and abstractions so as not to couple to strongly to either use-case.
    """

    def __init__(
        self,
        weaviate_version: _ServerVersion,
        consistency_level: Optional[ConsistencyLevel],
    ):
        super().__init__(weaviate_version, consistency_level, False)

    def __single_vec(self, vectors: Optional[VECTORS]) -> Optional[bytes]:
        if not _is_1d_vector(vectors):
            return None
        return _Pack.single(vectors)

    def __multi_vec(self, vectors: Optional[VECTORS]) -> Optional[List[base_pb2.Vectors]]:
        if vectors is None or _is_1d_vector(vectors):
            return None
        # pylance fails to type narrow TypeGuard in _is_1d_vector properly
        vectors = cast(Mapping[str, Union[Sequence[float], Sequence[Sequence[float]]]], vectors)
        return [
            base_pb2.Vectors(name=name, vector_bytes=packing.bytes_, type=packing.type_)
            for name, vec_or_vecs in vectors.items()
            if (packing := _Pack.parse_single_or_multi_vec(vec_or_vecs))
        ]

    def __grpc_objects(self, objects: List[_BatchObject]) -> List[batch_pb2.BatchObject]:
        return [
            batch_pb2.BatchObject(
                collection=obj.collection,
                uuid=(str(obj.uuid) if obj.uuid is not None else str(uuid_package.uuid4())),
                properties=(
                    self.__translate_properties_from_python_to_grpc(
                        obj.properties,
                        obj.references if obj.references is not None else {},
                    )
                    if obj.properties is not None
                    else None
                ),
                tenant=obj.tenant,
                vector_bytes=self.__single_vec(obj.vector),
                vectors=self.__multi_vec(obj.vector),
            )
            for obj in objects
        ]

    def objects(
        self,
        connection: Connection,
        *,
        objects: List[_BatchObject],
        timeout: Union[int, float],
        max_retries: float,
    ) -> executor.Result[BatchObjectReturn]:
        """Insert multiple objects into Weaviate through the gRPC API.

        Args:
            connection: The connection to the Weaviate instance.
            objects: A list of `WeaviateObject` containing the data of the objects to be inserted. The class name must be
                provided for each object, and the UUID is optional. If no UUID is provided, one will be generated for each object.
                The UUIDs of the inserted objects will be returned in the `uuids` attribute of the returned `_BatchReturn` object.
                The UUIDs of the objects that failed to be inserted will be returned in the `errors` attribute of the returned `_BatchReturn` object.
            timeout: The timeout in seconds for the request.
            max_retries: The maximum number of retries in case of a failure.
        """
        weaviate_objs = self.__grpc_objects(objects)
        start = time.time()

        def resp(errors: Dict[int, str]) -> BatchObjectReturn:
            if len(errors) == len(weaviate_objs):
                # Escape sequence (backslash) not allowed in expression portion of f-string prior to Python 3.12: pylance
                raise WeaviateInsertManyAllFailedError(
                    "Here is the set of all errors: {}".format(
                        "\n".join(err for err in set(errors.values()))
                    )
                )

            elapsed_time = time.time() - start
            all_responses: List[Union[uuid_package.UUID, ErrorObject]] = cast(
                List[Union[uuid_package.UUID, ErrorObject]],
                list(range(len(weaviate_objs))),
            )
            return_success: Dict[int, uuid_package.UUID] = {}
            return_errors: Dict[int, ErrorObject] = {}
            for idx, weav_obj in enumerate(weaviate_objs):
                obj = objects[idx]
                if idx in errors:
                    error = ErrorObject(
                        errors[idx],
                        BatchObject._from_internal(obj),
                        original_uuid=obj.uuid,
                    )
                    return_errors[obj.index] = error
                    all_responses[idx] = error
                else:
                    success = uuid_package.UUID(weav_obj.uuid)
                    return_success[obj.index] = success
                    all_responses[idx] = success

            return BatchObjectReturn(
                uuids=return_success,
                errors=return_errors,
                has_errors=len(errors) > 0,
                _all_responses=all_responses,
                elapsed_seconds=elapsed_time,
            )

        request = batch_pb2.BatchObjectsRequest(
            objects=weaviate_objs,
            consistency_level=self._consistency_level,
        )
        return executor.execute(
            response_callback=resp,
            method=connection.grpc_batch_objects,
            request=request,
            timeout=timeout,
            max_retries=max_retries,
        )

    def __translate_properties_from_python_to_grpc(
        self, data: Dict[str, Any], refs: ReferenceInputs
    ) -> batch_pb2.BatchObject.Properties:
        _validate_props(data)

        multi_target: List[batch_pb2.BatchObject.MultiTargetRefProps] = []
        single_target: List[batch_pb2.BatchObject.SingleTargetRefProps] = []
        non_ref_properties: Struct = Struct()
        bool_arrays: List[base_pb2.BooleanArrayProperties] = []
        text_arrays: List[base_pb2.TextArrayProperties] = []
        int_arrays: List[base_pb2.IntArrayProperties] = []
        float_arrays: List[base_pb2.NumberArrayProperties] = []
        object_properties: List[base_pb2.ObjectProperties] = []
        object_array_properties: List[base_pb2.ObjectArrayProperties] = []
        empty_lists: List[str] = []

        for key, ref in refs.items():
            if isinstance(ref, ReferenceToMulti):
                multi_target.append(
                    batch_pb2.BatchObject.MultiTargetRefProps(
                        uuids=ref.uuids_str,
                        target_collection=ref.target_collection,
                        prop_name=key,
                    )
                )
            elif isinstance(ref, str) or isinstance(ref, uuid_package.UUID):
                single_target.append(
                    batch_pb2.BatchObject.SingleTargetRefProps(uuids=[str(ref)], prop_name=key)
                )
            elif isinstance(ref, list):
                single_target.append(
                    batch_pb2.BatchObject.SingleTargetRefProps(
                        uuids=[str(v) for v in ref], prop_name=key
                    )
                )
            else:
                raise WeaviateInvalidInputError(f"Invalid reference: {ref}")

        for key, entry in data.items():
            if isinstance(entry, dict):
                parsed = self.__translate_properties_from_python_to_grpc(entry, {})
                object_properties.append(
                    base_pb2.ObjectProperties(
                        prop_name=key,
                        value=base_pb2.ObjectPropertiesValue(
                            non_ref_properties=parsed.non_ref_properties,
                            int_array_properties=parsed.int_array_properties,
                            text_array_properties=parsed.text_array_properties,
                            number_array_properties=parsed.number_array_properties,
                            boolean_array_properties=parsed.boolean_array_properties,
                            object_properties=parsed.object_properties,
                            object_array_properties=parsed.object_array_properties,
                            empty_list_props=parsed.empty_list_props,
                        ),
                    )
                )
            elif isinstance(entry, list) and len(entry) == 0:
                empty_lists.append(key)
            elif isinstance(entry, list) and isinstance(entry[0], dict):
                entry = cast(List[Dict[str, Any]], entry)
                object_array_properties.append(
                    base_pb2.ObjectArrayProperties(
                        values=[
                            base_pb2.ObjectPropertiesValue(
                                non_ref_properties=parsed.non_ref_properties,
                                int_array_properties=parsed.int_array_properties,
                                text_array_properties=parsed.text_array_properties,
                                number_array_properties=parsed.number_array_properties,
                                boolean_array_properties=parsed.boolean_array_properties,
                                object_properties=parsed.object_properties,
                                object_array_properties=parsed.object_array_properties,
                                empty_list_props=parsed.empty_list_props,
                            )
                            for v in entry
                            if (parsed := self.__translate_properties_from_python_to_grpc(v, {}))
                        ],
                        prop_name=key,
                    )
                )
            elif isinstance(entry, list) and isinstance(entry[0], bool):
                bool_arrays.append(base_pb2.BooleanArrayProperties(prop_name=key, values=entry))
            elif isinstance(entry, list) and isinstance(entry[0], str):
                text_arrays.append(base_pb2.TextArrayProperties(prop_name=key, values=entry))
            elif isinstance(entry, list) and isinstance(entry[0], datetime.datetime):
                text_arrays.append(
                    base_pb2.TextArrayProperties(
                        prop_name=key, values=[_datetime_to_string(x) for x in entry]
                    )
                )
            elif isinstance(entry, list) and isinstance(entry[0], uuid_package.UUID):
                text_arrays.append(
                    base_pb2.TextArrayProperties(prop_name=key, values=[str(x) for x in entry])
                )
            elif isinstance(entry, list) and isinstance(entry[0], int):
                int_arrays.append(base_pb2.IntArrayProperties(prop_name=key, values=entry))
            elif isinstance(entry, list) and isinstance(entry[0], float):
                values_bytes = struct.pack("{}d".format(len(entry)), *entry)
                float_arrays.append(
                    base_pb2.NumberArrayProperties(prop_name=key, values_bytes=values_bytes)
                )
            elif isinstance(entry, GeoCoordinate):
                non_ref_properties.update({key: entry._to_dict()})
            elif isinstance(entry, PhoneNumber):
                non_ref_properties.update({key: entry._to_dict()})
            else:
                non_ref_properties.update({key: _serialize_primitive(entry)})

        return batch_pb2.BatchObject.Properties(
            non_ref_properties=non_ref_properties,
            multi_target_ref_props=multi_target,
            single_target_ref_props=single_target,
            text_array_properties=text_arrays,
            number_array_properties=float_arrays,
            int_array_properties=int_arrays,
            boolean_array_properties=bool_arrays,
            object_properties=object_properties,
            object_array_properties=object_array_properties,
            empty_list_props=empty_lists,
        )


def _validate_props(props: Dict[str, Any]) -> None:
    if "id" in props or "vector" in props:
        raise WeaviateInsertInvalidPropertyError(props)


def _serialize_primitive(value: Any) -> Any:
    if isinstance(value, uuid_package.UUID):
        return str(value)
    if isinstance(value, datetime.datetime):
        return _datetime_to_string(value)
    if isinstance(value, list):
        return [_serialize_primitive(val) for val in value]

    return value
