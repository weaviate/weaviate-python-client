import datetime
import uuid as uuid_package
from typing import Any, List, Dict, Optional, Tuple, Union, cast

import grpc
from google.protobuf.struct_pb2 import Struct
from requests import Response

from weaviate.collection.classes.batch import Error, _BatchObject, _BatchReference, _BatchReturn
from weaviate.collection.classes.config import ConsistencyLevel
from weaviate.collection.classes.internal import _get_consistency_level, Reference
from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException, WeaviateGRPCException
from weaviate.util import _datetime_to_string
from weaviate_grpc import weaviate_pb2


class _BatchGRPC:
    """This class is used to insert multiple objects into Weaviate using the gRPC API.

    It is used within the `_Data` and `_Batch` classes hence the necessary generalities
    and abstractions so as not to couple to strongly to either use-case.
    """

    def __init__(self, connection: Connection, consistency_level: Optional[ConsistencyLevel]):
        self.__connection = connection
        self.__consistency_level = consistency_level

    def objects(self, objects: List[_BatchObject]) -> _BatchReturn:
        """Insert multiple objects into Weaviate through the gRPC API.

        Parameters:
            - objects: A list of `WeaviateObject` containing the data of the objects to be inserted. The class name must be
            provided for each object, and the UUID is optional. If no UUID is provided, one will be generated for each object.
            The UUIDs of the inserted objects will be returned in the `uuids` attribute of the returned `_BatchReturn` object.
            The UUIDs of the objects that failed to be inserted will be returned in the `errors` attribute of the returned `_BatchReturn` object.
            - tenant: The tenant to be used for this batch operation
        """
        weaviate_objs: List[weaviate_pb2.BatchObject] = [
            weaviate_pb2.BatchObject(
                class_name=obj.class_name,
                vector=obj.vector,
                uuid=str(obj.uuid) if obj.uuid is not None else str(uuid_package.uuid4()),
                properties=self.__parse_properties_grpc(obj.properties),
                tenant=obj.tenant,
            )
            for obj in objects
        ]

        errors = self.__send_batch(weaviate_objs)

        all_responses: List[Union[uuid_package.UUID, Error]] = cast(
            List[Union[uuid_package.UUID, Error]], list(range(len(weaviate_objs)))
        )
        return_success: Dict[int, uuid_package.UUID] = {}
        return_errors: Dict[int, Error] = {}

        for idx, obj in enumerate(weaviate_objs):
            if idx in errors:
                error = Error(errors[idx], original_uuid=objects[idx].uuid)
                return_errors[idx] = error
                all_responses[idx] = error
            else:
                success = uuid_package.UUID(obj.uuid)
                return_success[idx] = success
                all_responses[idx] = success

        return _BatchReturn(
            uuids=return_success,
            errors=return_errors,
            has_errors=len(errors) > 0,
            all_responses=all_responses,
        )

    def references(self, references: List[_BatchReference]) -> Response:
        params: Dict[str, str] = {}
        if self.__consistency_level is not None:
            params["consistency_level"] = self.__consistency_level

        refs = [
            {"from": ref.from_, "to": ref.to}
            if ref.tenant is None
            else {"from": ref.from_, "to": ref.to, "tenant": ref.tenant}
            for ref in references
        ]

        response = self.__connection.post(
            path="/batch/references", weaviate_object=refs, params=params
        )
        if response.status_code == 200:
            return response
        raise UnexpectedStatusCodeException("Send ref batch", response)

    def __send_batch(self, batch: List[weaviate_pb2.BatchObject]) -> Dict[int, str]:
        metadata: Optional[Tuple[Tuple[str, str]]] = None
        access_token = self.__connection.get_current_bearer_token()
        if len(access_token) > 0:
            metadata = (("authorization", access_token),)
        try:
            assert self.__connection.grpc_stub is not None
            res, _ = self.__connection.grpc_stub.BatchObjects.with_call(
                weaviate_pb2.BatchObjectsRequest(
                    objects=batch,
                    consistency_level=_get_consistency_level(self.__consistency_level),
                ),
                metadata=metadata,
            )

            objects: Dict[int, str] = {}
            for result in res.results:
                objects[result.index] = result.error
            return objects
        except grpc.RpcError as e:
            raise WeaviateGRPCException(e.details())

    def __parse_properties_grpc(self, data: Dict[str, Any]) -> weaviate_pb2.BatchObject.Properties:
        multi_target: List[weaviate_pb2.BatchObject.RefPropertiesMultiTarget] = []
        single_target: List[weaviate_pb2.BatchObject.RefPropertiesSingleTarget] = []
        non_ref_properties: Struct = Struct()
        bool_arrays: List[weaviate_pb2.BooleanArrayProperties] = []
        text_arrays: List[weaviate_pb2.TextArrayProperties] = []
        int_arrays: List[weaviate_pb2.IntArrayProperties] = []
        float_arrays: List[weaviate_pb2.NumberArrayProperties] = []
        for key, val in data.items():
            if isinstance(val, Reference):
                if val.is_multi_target:
                    multi_target.append(
                        weaviate_pb2.BatchObject.RefPropertiesMultiTarget(
                            uuids=val.uuids_str,
                            target_collection=val.target_collection,
                            prop_name=key,
                        )
                    )
                else:
                    single_target.append(
                        weaviate_pb2.BatchObject.RefPropertiesSingleTarget(
                            uuids=val.uuids_str, prop_name=key
                        )
                    )
            elif isinstance(val, list) and isinstance(val[0], bool):
                bool_arrays.append(weaviate_pb2.BooleanArrayProperties(prop_name=key, values=val))
            elif isinstance(val, list) and isinstance(val[0], str):
                text_arrays.append(weaviate_pb2.TextArrayProperties(prop_name=key, values=val))
            elif isinstance(val, list) and isinstance(val[0], datetime.datetime):
                text_arrays.append(
                    weaviate_pb2.TextArrayProperties(
                        prop_name=key, values=[_datetime_to_string(x) for x in val]
                    )
                )
            elif isinstance(val, list) and isinstance(val[0], uuid_package.UUID):
                text_arrays.append(
                    weaviate_pb2.TextArrayProperties(prop_name=key, values=[str(x) for x in val])
                )
            elif isinstance(val, list) and isinstance(val[0], int):
                int_arrays.append(weaviate_pb2.IntArrayProperties(prop_name=key, values=val))
            elif isinstance(val, list) and isinstance(val[0], float):
                float_arrays.append(weaviate_pb2.NumberArrayProperties(prop_name=key, values=val))
            else:
                non_ref_properties.update({key: val})

        return weaviate_pb2.BatchObject.Properties(
            non_ref_properties=non_ref_properties,
            ref_props_multi=multi_target,
            ref_props_single=single_target,
            text_array_properties=text_arrays,
            number_array_properties=float_arrays,
            int_array_properties=int_arrays,
            boolean_array_properties=bool_arrays,
        )
