import datetime
import struct
import time
import uuid as uuid_package
from typing import Any, Dict, List, Optional, Union, cast

from grpc.aio import AioRpcError  # type: ignore
from google.protobuf.struct_pb2 import Struct

from weaviate.collections.classes.batch import (
    ErrorObject,
    _BatchObject,
    BatchObjectReturn,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.types import GeoCoordinate, PhoneNumber
from weaviate.collections.classes.internal import ReferenceToMulti, ReferenceInputs
from weaviate.collections.grpc.shared import _BaseGRPC
from weaviate.connect import ConnectionV4
from weaviate.exceptions import (
    WeaviateBatchError,
    WeaviateInsertInvalidPropertyError,
    WeaviateInsertManyAllFailedError,
    WeaviateInvalidInputError,
)
from weaviate.proto.v1 import batch_pb2, base_pb2
from weaviate.util import _datetime_to_string, _get_vector_v4


def _pack_named_vectors(vectors: Dict[str, List[float]]) -> List[base_pb2.Vectors]:
    return [
        base_pb2.Vectors(
            name=name,
            vector_bytes=struct.pack("{}f".format(len(vector)), *vector),
        )
        for name, vector in vectors.items()
    ]


class _BatchGRPC(_BaseGRPC):
    """This class is used to insert multiple objects into Weaviate using the gRPC API.

    It is used within the `_Data` and `_Batch` classes hence the necessary generalities
    and abstractions so as not to couple to strongly to either use-case.
    """

    def __init__(self, connection: ConnectionV4, consistency_level: Optional[ConsistencyLevel]):
        super().__init__(connection, consistency_level)

    def __grpc_objects(self, objects: List[_BatchObject]) -> List[batch_pb2.BatchObject]:
        def pack_vector(vector: Any) -> bytes:
            vector_list = _get_vector_v4(vector)
            return struct.pack("{}f".format(len(vector_list)), *vector_list)

        return [
            batch_pb2.BatchObject(
                collection=obj.collection,
                vector_bytes=(
                    pack_vector(obj.vector)
                    if obj.vector is not None and isinstance(obj.vector, list)
                    else None
                ),
                uuid=str(obj.uuid) if obj.uuid is not None else str(uuid_package.uuid4()),
                properties=(
                    self.__translate_properties_from_python_to_grpc(
                        obj.properties,
                        obj.references if obj.references is not None else {},
                    )
                    if obj.properties is not None
                    else None
                ),
                tenant=obj.tenant,
                vectors=(
                    _pack_named_vectors(obj.vector)
                    if obj.vector is not None and isinstance(obj.vector, dict)
                    else None
                ),
            )
            for obj in objects
        ]

    async def objects(
        self, objects: List[_BatchObject], timeout: Union[int, float]
    ) -> BatchObjectReturn:
        """Insert multiple objects into Weaviate through the gRPC API.

        Parameters:
            `objects`
                A list of `WeaviateObject` containing the data of the objects to be inserted. The class name must be
                provided for each object, and the UUID is optional. If no UUID is provided, one will be generated for each object.
                The UUIDs of the inserted objects will be returned in the `uuids` attribute of the returned `_BatchReturn` object.
                The UUIDs of the objects that failed to be inserted will be returned in the `errors` attribute of the returned `_BatchReturn` object.
            `tenant`
                The tenant to be used for this batch operation
        """
        weaviate_objs = self.__grpc_objects(objects)

        start = time.time()
        errors = await self.__send_batch(weaviate_objs, timeout=timeout)
        elapsed_time = time.time() - start

        if len(errors) == len(weaviate_objs):
            # Escape sequence (backslash) not allowed in expression portion of f-string prior to Python 3.12: pylance
            raise WeaviateInsertManyAllFailedError(
                "Here is the set of all errors: {}".format(
                    "\n".join(err for err in set(errors.values()))
                )
            )

        all_responses: List[Union[uuid_package.UUID, ErrorObject]] = cast(
            List[Union[uuid_package.UUID, ErrorObject]], list(range(len(weaviate_objs)))
        )
        return_success: Dict[int, uuid_package.UUID] = {}
        return_errors: Dict[int, ErrorObject] = {}

        for idx, weav_obj in enumerate(weaviate_objs):
            obj = objects[idx]
            if idx in errors:
                error = ErrorObject(errors[idx], obj, original_uuid=obj.uuid)
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

    async def __send_batch(
        self, batch: List[batch_pb2.BatchObject], timeout: Union[int, float]
    ) -> Dict[int, str]:
        metadata = self._get_metadata()
        try:
            assert self._connection.grpc_stub is not None
            res = await self._connection.grpc_stub.BatchObjects(
                batch_pb2.BatchObjectsRequest(
                    objects=batch,
                    consistency_level=self._consistency_level,
                ),
                metadata=metadata,
                timeout=timeout,
            )
            res = cast(batch_pb2.BatchObjectsReply, res)

            objects: Dict[int, str] = {}
            for result in res.errors:
                objects[result.index] = result.error
            return objects
        except AioRpcError as e:
            raise WeaviateBatchError(str(e)) from e

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
                        uuids=ref.uuids_str, target_collection=ref.target_collection, prop_name=key
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
