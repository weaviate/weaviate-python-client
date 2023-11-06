import datetime
import uuid as uuid_package
import time
from typing import Any, List, Dict, Union, cast

import grpc  # type: ignore
from google.protobuf.struct_pb2 import Struct

from weaviate.collections.classes.batch import (
    ErrorObject,
    _BatchObject,
    BatchObjectReturn,
)
from weaviate.collections.classes.internal import _Reference
from weaviate.collections.grpc.shared import _BaseGRPC
from weaviate.exceptions import WeaviateQueryException, WeaviateInsertInvalidPropertyError
from weaviate.util import _datetime_to_string, get_vector
from weaviate.proto.v1 import batch_pb2, base_pb2


class _BatchGRPC(_BaseGRPC):
    """This class is used to insert multiple objects into Weaviate using the gRPC API.

    It is used within the `_Data` and `_Batch` classes hence the necessary generalities
    and abstractions so as not to couple to strongly to either use-case.
    """

    def objects(self, objects: List[_BatchObject]) -> BatchObjectReturn:
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
        weaviate_objs: List[batch_pb2.BatchObject] = [
            batch_pb2.BatchObject(
                collection=obj.collection,
                vector=get_vector(obj.vector) if obj.vector is not None else None,
                uuid=str(obj.uuid) if obj.uuid is not None else str(uuid_package.uuid4()),
                properties=self.__translate_properties_from_python_to_grpc(obj.properties, False),
                tenant=obj.tenant,
            )
            for obj in objects
        ]

        start = time.time()
        errors = self.__send_batch(weaviate_objs)
        elapsed_time = time.time() - start

        all_responses: List[Union[uuid_package.UUID, ErrorObject]] = cast(
            List[Union[uuid_package.UUID, ErrorObject]], list(range(len(weaviate_objs)))
        )
        return_success: Dict[int, uuid_package.UUID] = {}
        return_errors: Dict[int, ErrorObject] = {}

        for idx, obj in enumerate(weaviate_objs):
            if idx in errors:
                error = ErrorObject(errors[idx], objects[idx], original_uuid=objects[idx].uuid)
                return_errors[idx] = error
                all_responses[idx] = error
            else:
                success = uuid_package.UUID(obj.uuid)
                return_success[idx] = success
                all_responses[idx] = success

        return BatchObjectReturn(
            uuids=return_success,
            errors=return_errors,
            has_errors=len(errors) > 0,
            all_responses=all_responses,
            elapsed_seconds=elapsed_time,
        )

    def __send_batch(self, batch: List[batch_pb2.BatchObject]) -> Dict[int, str]:
        metadata = self._get_metadata()
        try:
            assert self._connection.grpc_stub is not None
            res: batch_pb2.BatchObjectsReply
            res, _ = self._connection.grpc_stub.BatchObjects.with_call(
                batch_pb2.BatchObjectsRequest(
                    objects=batch,
                    consistency_level=self._consistency_level,
                ),
                metadata=metadata,
            )

            objects: Dict[int, str] = {}
            for result in res.errors:
                objects[result.index] = result.error
            return objects
        except grpc.RpcError as e:
            raise WeaviateQueryException(e.details())

    def __translate_properties_from_python_to_grpc(
        self, data: Dict[str, Any], clean_props: bool
    ) -> batch_pb2.BatchObject.Properties:
        _validate_props(data, clean_props)

        multi_target: List[batch_pb2.BatchObject.MultiTargetRefProps] = []
        single_target: List[batch_pb2.BatchObject.SingleTargetRefProps] = []
        non_ref_properties: Struct = Struct()
        bool_arrays: List[base_pb2.BooleanArrayProperties] = []
        text_arrays: List[base_pb2.TextArrayProperties] = []
        int_arrays: List[base_pb2.IntArrayProperties] = []
        float_arrays: List[base_pb2.NumberArrayProperties] = []
        object_properties: List[base_pb2.ObjectProperties] = []
        object_array_properties: List[base_pb2.ObjectArrayProperties] = []
        for key, val in data.items():
            if isinstance(val, _Reference):
                if val.is_multi_target:
                    multi_target.append(
                        batch_pb2.BatchObject.MultiTargetRefProps(
                            uuids=val.uuids_str,
                            target_collection=val.target_collection,
                            prop_name=key,
                        )
                    )
                else:
                    single_target.append(
                        batch_pb2.BatchObject.SingleTargetRefProps(
                            uuids=val.uuids_str, prop_name=key
                        )
                    )
            elif isinstance(val, dict):
                parsed = self.__translate_properties_from_python_to_grpc(val, clean_props)
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
                        ),
                    )
                )
            elif isinstance(val, list) and isinstance(val[0], dict):
                val = cast(List[Dict[str, Any]], val)
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
                            )
                            for v in val
                            if (
                                parsed := self.__translate_properties_from_python_to_grpc(
                                    v, clean_props
                                )
                            )
                        ],
                        prop_name=key,
                    )
                )
            elif isinstance(val, list) and isinstance(val[0], bool):
                bool_arrays.append(base_pb2.BooleanArrayProperties(prop_name=key, values=val))
            elif isinstance(val, list) and isinstance(val[0], str):
                text_arrays.append(base_pb2.TextArrayProperties(prop_name=key, values=val))
            elif isinstance(val, list) and isinstance(val[0], datetime.datetime):
                text_arrays.append(
                    base_pb2.TextArrayProperties(
                        prop_name=key, values=[_datetime_to_string(x) for x in val]
                    )
                )
            elif isinstance(val, list) and isinstance(val[0], uuid_package.UUID):
                text_arrays.append(
                    base_pb2.TextArrayProperties(prop_name=key, values=[str(x) for x in val])
                )
            elif isinstance(val, list) and isinstance(val[0], int):
                int_arrays.append(base_pb2.IntArrayProperties(prop_name=key, values=val))
            elif isinstance(val, list) and isinstance(val[0], float):
                float_arrays.append(base_pb2.NumberArrayProperties(prop_name=key, values=val))
            else:
                non_ref_properties.update({key: _serialize_primitive(val)})

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
        )


def _validate_props(props: Dict[str, Any], clean_props: bool) -> None:
    should_throw = False
    if "id" in props:
        if clean_props:
            del props["id"]
        else:
            should_throw = True
    if "vector" in props:
        if clean_props:
            del props["vector"]
        else:
            should_throw = True
    if should_throw:
        raise WeaviateInsertInvalidPropertyError(props)


def _serialize_primitive(value: Any) -> Any:
    if isinstance(value, uuid_package.UUID):
        return str(value)
    if isinstance(value, datetime.datetime):
        return _datetime_to_string(value)
    if isinstance(value, list):
        return [_serialize_primitive(val) for val in value]
    return value
