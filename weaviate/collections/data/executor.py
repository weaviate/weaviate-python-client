import asyncio
import datetime
import uuid as uuid_package
from typing import (
    Awaitable,
    Dict,
    Any,
    Optional,
    List,
    Mapping,
    Sequence,
    Tuple,
    Union,
    cast,
    overload,
)

from weaviate.collections.classes.batch import (
    DeleteManyObject,
    _BatchObject,
    _BatchReference,
    BatchObjectReturn,
    BatchReferenceReturn,
    DeleteManyReturn,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.data import DataObject, DataReferences
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.internal import (
    _Reference,
    ReferenceToMulti,
    SingleReferenceInput,
    ReferenceInput,
    ReferenceInputs,
)
from weaviate.collections.classes.types import (
    GeoCoordinate,
    PhoneNumber,
    _PhoneNumber,
    Properties,
    WeaviateField,
)
from weaviate.connect.executor import execute
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionAsync
from weaviate.logger import logger
from weaviate.types import BEACON, UUID, VECTORS
from weaviate.util import _datetime_to_string, _get_vector_v4
from weaviate.validator import _validate_input, _ValidateArgument

from weaviate.collections.batch.grpc_batch_delete import _BatchDeleteGRPC
from weaviate.collections.batch.grpc_batch_objects import _BatchGRPC
from weaviate.collections.batch.rest import _BatchREST
from weaviate.collections.filters import _FilterToGRPC
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1.batch_delete_pb2 import BatchDeleteRequest, BatchDeleteReply
from weaviate.util import _ServerVersion, _WeaviateUUIDInt


class _DataExecutor:
    def __init__(
        self,
        weaviate_version: _ServerVersion,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        validate_arguments: bool,
    ) -> None:
        self.__name = name
        self.__consistency_level = consistency_level
        self.__tenant = tenant
        self.__validate_arguments = validate_arguments
        self.__batch_grpc = _BatchGRPC(
            weaviate_version=weaviate_version,
            consistency_level=consistency_level,
        )
        self.__batch_rest = _BatchREST(consistency_level=consistency_level)
        self.__batch_delete_grpc = _BatchDeleteGRPC(
            weaviate_version=weaviate_version, consistency_level=consistency_level
        )

    def insert(
        self,
        connection: ConnectionAsync,
        *,
        properties: Properties,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID],
        vector: Optional[VECTORS],
    ) -> Awaitable[uuid_package.UUID]:
        path = "/objects"

        if self.__validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID, None], name="uuid", value=uuid),
                    _ValidateArgument(expected=[Mapping], name="properties", value=properties),
                    _ValidateArgument(
                        expected=[Mapping, None], name="references", value=references
                    ),
                ],
            )
        props = self.__serialize_props(properties) if properties is not None else {}
        refs = self.__serialize_refs(references) if references is not None else {}
        weaviate_obj: Dict[str, Any] = {
            "class": self.__name,
            "properties": {**props, **refs},
            "id": str(uuid if uuid is not None else uuid_package.uuid4()),
        }
        if vector is not None:
            weaviate_obj = self.__parse_vector(weaviate_obj, vector)

        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)
        return execute(
            response_callback=lambda res: uuid_package.UUID(weaviate_obj["id"]),
            method=connection.post,
            path=path,
            weaviate_object=weaviate_obj,
            params=params,
            error_msg="Object was not added",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="insert object"),
        )

    def insert_many(
        self,
        connection: ConnectionAsync,
        *,
        objects: Sequence[Union[Properties, DataObject[Properties, Optional[ReferenceInputs]]]],
    ) -> Awaitable[BatchObjectReturn]:
        objs = [
            (
                _BatchObject(
                    collection=self.__name,
                    vector=obj.vector,
                    uuid=str(obj.uuid if obj.uuid is not None else uuid_package.uuid4()),
                    properties=cast(dict, obj.properties),
                    tenant=self.__tenant,
                    references=obj.references,
                    index=idx,
                )
                if isinstance(obj, DataObject)
                else _BatchObject(
                    collection=self.__name,
                    vector=None,
                    uuid=str(uuid_package.uuid4()),
                    properties=cast(dict, obj),
                    tenant=self.__tenant,
                    references=None,
                    index=idx,
                )
            )
            for idx, obj in enumerate(objects)
        ]

        def resp(res: BatchObjectReturn) -> BatchObjectReturn:
            if (n_obj_errs := len(res.errors)) > 0:
                logger.error(
                    {
                        "message": f"Failed to send {n_obj_errs} objects in a batch of {len(objs)}. Please inspect the errors variable of the returned object for more information.",
                        "errors": res.errors,
                    }
                )
            return res

        return execute(
            response_callback=resp,
            method=self.__batch_grpc.objects,
            connection=connection,
            objects=objs,
            timeout=connection.timeout_config.insert,
        )

    def exists(self, connection: ConnectionAsync, *, uuid: UUID) -> Awaitable[bool]:
        _validate_input(_ValidateArgument(expected=[UUID], name="uuid", value=uuid))
        path = "/objects/" + self.__name + "/" + str(uuid)
        params = self.__apply_context({})
        return execute(
            response_callback=lambda res: res.status_code == 204,
            method=connection.head,
            path=path,
            params=params,
            error_msg="object existence",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="object existence"),
        )

    def replace(
        self,
        connection: ConnectionAsync,
        *,
        uuid: UUID,
        properties: Properties,
        references: Optional[ReferenceInputs],
        vector: Optional[VECTORS],
    ) -> Awaitable[None]:
        path = f"/objects/{self.__name}/{uuid}"

        if self.__validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID], name="uuid", value=uuid),
                    _ValidateArgument(expected=[Mapping], name="properties", value=properties),
                    _ValidateArgument(
                        expected=[Mapping, None], name="references", value=references
                    ),
                ]
            )
        props = self.__serialize_props(properties) if properties is not None else {}
        refs = self.__serialize_refs(references) if references is not None else {}
        weaviate_obj: Dict[str, Any] = {
            "class": self.__name,
            "properties": {**props, **refs},
        }
        if vector is not None:
            weaviate_obj = self.__parse_vector(weaviate_obj, vector)

        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)
        weaviate_obj["id"] = str(uuid)  # must add ID to payload for PUT request
        return execute(
            response_callback=lambda res: None,
            method=connection.put,
            path=path,
            weaviate_object=weaviate_obj,
            params=params,
            error_msg="Object was not replaced.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="replace object"),
        )

    def update(
        self,
        connection: ConnectionAsync,
        *,
        uuid: UUID,
        properties: Optional[Properties],
        references: Optional[ReferenceInputs],
        vector: Optional[VECTORS],
    ) -> Awaitable[None]:
        path = f"/objects/{self.__name}/{uuid}"

        if self.__validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID], name="uuid", value=uuid),
                    _ValidateArgument(
                        expected=[Mapping, None], name="properties", value=properties
                    ),
                    _ValidateArgument(
                        expected=[Mapping, None], name="references", value=references
                    ),
                ],
            )
        props = self.__serialize_props(properties) if properties is not None else {}
        refs = self.__serialize_refs(references) if references is not None else {}
        weaviate_obj: Dict[str, Any] = {"class": self.__name, "properties": {**props, **refs}}
        if vector is not None:
            weaviate_obj = self.__parse_vector(weaviate_obj, vector)

        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)
        return execute(
            response_callback=lambda res: None,
            method=connection.patch,
            path=path,
            weaviate_object=weaviate_obj,
            params=params,
            error_msg="Object was not updated.",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 204], error="update object"),
        )

    def reference_add(
        self,
        connection: ConnectionAsync,
        *,
        from_uuid: UUID,
        from_property: str,
        to: SingleReferenceInput,
    ) -> Awaitable[None]:
        params: Dict[str, str] = {}

        path = f"/objects/{self.__name}/{from_uuid}/references/{from_property}"

        if self.__validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID], name="from_uuid", value=from_uuid),
                    _ValidateArgument(expected=[str], name="from_property", value=from_property),
                    _ValidateArgument(
                        expected=[UUID, ReferenceToMulti], name="references", value=to
                    ),
                ],
            )
        if isinstance(to, ReferenceToMulti):
            ref = _Reference(target_collection=to.target_collection, uuids=to.uuids)
        else:
            ref = _Reference(target_collection=None, uuids=to)

        if ref.is_one_to_many:
            raise WeaviateInvalidInputError(
                "reference_add does not support adding multiple objects to a reference at once. Use reference_add_many or reference_replace instead."
            )
        if isinstance(connection, ConnectionAsync):

            async def _execute() -> None:
                await asyncio.gather(
                    *[
                        connection.post(
                            path=path,
                            weaviate_object=beacon,
                            params=self.__apply_context(params),
                            error_msg="Reference was not added.",
                            status_codes=_ExpectedStatusCodes(
                                ok_in=200, error="add reference to object"
                            ),
                        )
                        for beacon in ref._to_beacons()
                    ]
                )

            return _execute()
        for beacon in ref._to_beacons():
            connection.post(
                path=path,
                weaviate_object=beacon,
                params=self._apply_context(params),
                error_msg="Reference was not added.",
                status_codes=_ExpectedStatusCodes(ok_in=200, error="add reference to object"),
            )

    def reference_add_many(
        self, connection: ConnectionAsync, *, refs: List[DataReferences]
    ) -> Awaitable[BatchReferenceReturn]:
        batch = [
            _BatchReference(
                from_=f"{BEACON}{self.__name}/{ref.from_uuid}/{ref.from_property}",
                to=beacon,
                tenant=self.__tenant,
                from_uuid=str(ref.from_uuid),
                to_uuid=None,  # not relevant here, this entry is only needed for the batch module
            )
            for ref in refs
            for beacon in ref._to_beacons()
        ]
        return self.__batch_rest.references(connection, references=list(batch))

    def reference_delete(
        self,
        connection: ConnectionAsync,
        *,
        from_uuid: UUID,
        from_property: str,
        to: SingleReferenceInput,
    ) -> Awaitable[None]:
        params: Dict[str, str] = {}
        path = f"/objects/{self.__name}/{from_uuid}/references/{from_property}"

        if self.__validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID], name="from_uuid", value=from_uuid),
                    _ValidateArgument(expected=[str], name="from_property", value=from_property),
                    _ValidateArgument(
                        expected=[UUID, ReferenceToMulti], name="references", value=to
                    ),
                ]
            )
        if isinstance(to, ReferenceToMulti):
            ref = _Reference(target_collection=to.target_collection, uuids=to.uuids)
        else:
            ref = _Reference(target_collection=None, uuids=to)

        if ref.is_one_to_many:
            raise WeaviateInvalidInputError(
                "reference_delete does not support deleting multiple objects from a reference at once. Use reference_replace instead."
            )
        if isinstance(connection, ConnectionAsync):

            async def _execute() -> None:
                await asyncio.gather(
                    *[
                        connection.delete(
                            path=path,
                            weaviate_object=beacon,
                            params=self.__apply_context(params),
                            error_msg="Reference was not deleted.",
                            status_codes=_ExpectedStatusCodes(
                                ok_in=204, error="delete reference from object"
                            ),
                        )
                        for beacon in ref._to_beacons()
                    ]
                )

            return _execute()
        for beacon in ref._to_beacons():
            connection.delete(
                path=path,
                weaviate_object=beacon,
                params=self._apply_context(params),
                error_msg="Reference was not deleted.",
                status_codes=_ExpectedStatusCodes(ok_in=204, error="delete reference from object"),
            )

    def reference_replace(
        self,
        connection: ConnectionAsync,
        *,
        from_uuid: UUID,
        from_property: str,
        to: ReferenceInput,
    ) -> Awaitable[None]:
        params: Dict[str, str] = {}
        path = f"/objects/{self.__name}/{from_uuid}/references/{from_property}"

        if self.__validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID], name="from_uuid", value=from_uuid),
                    _ValidateArgument(expected=[str], name="from_property", value=from_property),
                    _ValidateArgument(
                        expected=[
                            UUID,
                            ReferenceToMulti,
                            List[str],
                            List[uuid_package.UUID],
                            List[UUID],
                        ],
                        name="references",
                        value=to,
                    ),
                ]
            )
        if isinstance(to, ReferenceToMulti):
            ref = _Reference(target_collection=to.target_collection, uuids=to.uuids)
        else:
            ref = _Reference(target_collection=None, uuids=to)

        return execute(
            response_callback=lambda res: None,
            method=connection.put,
            path=path,
            weaviate_object=ref._to_beacons(),
            params=self.__apply_context(params),
            error_msg="Reference was not replaced.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="replace reference on object"),
        )

    def delete_by_id(self, connection: ConnectionAsync, *, uuid: UUID) -> Awaitable[bool]:
        path = f"/objects/{self.__name}/{uuid}"
        return execute(
            response_callback=lambda res: res.status_code == 204,
            method=connection.delete,
            path=path,
            params=self.__apply_context({}),
            error_msg="Object could not be deleted.",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="delete object"),
        )

    def delete_many(
        self,
        connection: ConnectionAsync,
        *,
        where: _Filters,
        verbose: bool = False,
        dry_run: bool = False,
    ) -> Awaitable[Union[DeleteManyReturn[List[DeleteManyObject]], DeleteManyReturn[None]]]:
        _ValidateArgument(expected=[_Filters], name="where", value=where)

        request = BatchDeleteRequest(
            collection=self.__name,
            consistency_level=self.__consistency_level,
            verbose=verbose,
            dry_run=dry_run,
            tenant=self.__tenant,
            filters=_FilterToGRPC.convert(where),
        )

        def resp(
            res: BatchDeleteReply,
        ) -> Union[DeleteManyReturn[List[DeleteManyObject]], DeleteManyReturn[None]]:
            if verbose:
                objects: List[DeleteManyObject] = [
                    DeleteManyObject(
                        uuid=_WeaviateUUIDInt(int.from_bytes(obj.uuid, byteorder="big")),
                        successful=obj.successful,
                        error=obj.error if obj.error != "" else None,
                    )
                    for obj in res.objects
                ]
                return DeleteManyReturn(
                    failed=res.failed,
                    successful=res.successful,
                    matches=res.matches,
                    objects=objects,
                )
            else:
                return DeleteManyReturn(
                    failed=res.failed, successful=res.successful, matches=res.matches, objects=None
                )

        return execute(
            response_callback=resp,
            method=connection.grpc_batch_delete,
            request=request,
        )

    def __apply_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self.__tenant is not None:
            params["tenant"] = self.__tenant
        if self.__consistency_level is not None:
            params["consistency_level"] = self.__consistency_level.value
        return params

    def __apply_context_to_params_and_object(
        self, params: Dict[str, Any], obj: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if self.__tenant is not None:
            obj["tenant"] = self.__tenant
        if self.__consistency_level is not None:
            params["consistency_level"] = self.__consistency_level.value
        return params, obj

    def __serialize_props(self, props: Properties) -> Dict[str, Any]:
        return {key: self.__serialize_primitive(val) for key, val in props.items()}

    def __serialize_refs(self, refs: ReferenceInputs) -> Dict[str, Any]:
        return {
            key: (
                val._to_beacons()
                if isinstance(val, _Reference) or isinstance(val, ReferenceToMulti)
                else _Reference(target_collection=None, uuids=val)._to_beacons()
            )
            for key, val in refs.items()
        }

    def __serialize_primitive(self, value: WeaviateField) -> Any:
        if isinstance(value, str) or isinstance(value, int) or isinstance(value, float):
            return value
        if isinstance(value, uuid_package.UUID):
            return str(value)
        if isinstance(value, datetime.datetime):
            return _datetime_to_string(value)
        if isinstance(value, GeoCoordinate):
            return value._to_dict()
        if isinstance(value, PhoneNumber):
            return value._to_dict()
        if isinstance(value, _PhoneNumber):
            raise WeaviateInvalidInputError(
                "Cannot use _PhoneNumber when inserting a phone number. Use PhoneNumber instead."
            )
        if isinstance(value, Mapping):
            return {key: self.__serialize_primitive(val) for key, val in value.items()}
        if isinstance(value, Sequence):
            return [self.__serialize_primitive(val) for val in value]
        if value is None:
            return value
        raise WeaviateInvalidInputError(
            f"Cannot serialize value of type {type(value)} to Weaviate."
        )

    def __parse_vector(self, obj: Dict[str, Any], vector: VECTORS) -> Dict[str, Any]:
        if isinstance(vector, dict):
            obj["vectors"] = {key: _get_vector_v4(val) for key, val in vector.items()}
        else:
            obj["vector"] = _get_vector_v4(vector)
        return obj
