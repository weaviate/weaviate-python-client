import asyncio
import datetime
import uuid as uuid_package
from typing import (
    Dict,
    Any,
    Optional,
    List,
    Mapping,
    Tuple,
    Sequence,
)

from weaviate.collections.batch.grpc_batch_delete import _BatchDeleteGRPC
from weaviate.collections.batch.grpc_batch_objects import _BatchGRPC
from weaviate.collections.batch.rest import _BatchREST
from weaviate.collections.classes.batch import (
    _BatchReference,
    BatchReferenceReturn,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.data import DataReferences
from weaviate.collections.classes.internal import (
    _Reference,
    ReferenceToMulti,
    ReferenceInputs,
)
from weaviate.collections.classes.types import (
    GeoCoordinate,
    PhoneNumber,
    _PhoneNumber,
    Properties,
    WeaviateField,
)
from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.types import BEACON, UUID
from weaviate.util import _datetime_to_string


class _Data:
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        validate_arguments: bool,
    ) -> None:
        self._connection = connection
        self.name = name
        self._consistency_level = consistency_level
        self._tenant = tenant
        self._validate_arguments = validate_arguments
        self._batch_grpc = _BatchGRPC(connection, consistency_level)
        self._batch_delete_grpc = _BatchDeleteGRPC(connection, consistency_level)
        self._batch_rest = _BatchREST(connection, consistency_level)

    async def _insert(self, weaviate_obj: Dict[str, Any]) -> uuid_package.UUID:
        path = "/objects"

        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)
        await self._connection.post(
            path=path,
            weaviate_object=weaviate_obj,
            params=params,
            error_msg="Object was not added",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="insert object"),
        )
        return uuid_package.UUID(weaviate_obj["id"])

    async def _exists(self, uuid: str) -> bool:
        path = "/objects/" + self.name + "/" + uuid

        params = self.__apply_context({})
        request = await self._connection.head(
            path=path,
            params=params,
            error_msg="object existence",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="object existence"),
        )
        return request.status_code == 204

    async def delete_by_id(self, uuid: UUID) -> bool:
        """Delete an object from the collection based on its UUID.

        Arguments:
            `uuid`
                The UUID of the object to delete, REQUIRED.
        """
        path = f"/objects/{self.name}/{uuid}"

        response = await self._connection.delete(
            path=path,
            params=self.__apply_context({}),
            error_msg="Object could not be deleted.",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="delete object"),
        )
        if response.status_code == 204:
            return True  # Successfully deleted
        else:
            assert response.status_code == 404
            return False  # did not exist

    async def _replace(self, weaviate_obj: Dict[str, Any], uuid: UUID) -> None:
        path = f"/objects/{self.name}/{uuid}"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)

        weaviate_obj["id"] = str(uuid)  # must add ID to payload for PUT request

        await self._connection.put(
            path=path,
            weaviate_object=weaviate_obj,
            params=params,
            error_msg="Object was not replaced.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="replace object"),
        )

    async def _update(self, weaviate_obj: Dict[str, Any], uuid: UUID) -> None:
        path = f"/objects/{self.name}/{uuid}"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)

        await self._connection.patch(
            path=path,
            weaviate_object=weaviate_obj,
            params=params,
            error_msg="Object was not updated.",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 204], error="update object"),
        )

    async def _reference_add(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"

        if ref.is_one_to_many:
            raise WeaviateInvalidInputError(
                "reference_add does not support adding multiple objects to a reference at once. Use reference_add_many or reference_replace instead."
            )
        await asyncio.gather(
            *[
                self._connection.post(
                    path=path,
                    weaviate_object=beacon,
                    params=self.__apply_context(params),
                    error_msg="Reference was not added.",
                    status_codes=_ExpectedStatusCodes(ok_in=200, error="add reference to object"),
                )
                for beacon in ref._to_beacons()
            ]
        )

    async def _reference_add_many(self, refs: List[DataReferences]) -> BatchReferenceReturn:
        batch = [
            _BatchReference(
                from_=f"{BEACON}{self.name}/{ref.from_uuid}/{ref.from_property}",
                to=beacon,
                tenant=self._tenant,
                from_uuid=str(ref.from_uuid),
            )
            for ref in refs
            for beacon in ref._to_beacons()
        ]
        return await self._batch_rest.references(list(batch))

    async def _reference_delete(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"

        if ref.is_one_to_many:
            raise WeaviateInvalidInputError(
                "reference_delete does not support deleting multiple objects from a reference at once. Use reference_replace instead."
            )
        await asyncio.gather(
            *[
                self._connection.delete(
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

    async def _reference_replace(
        self, from_uuid: UUID, from_property: str, ref: _Reference
    ) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"
        await self._connection.put(
            path=path,
            weaviate_object=ref._to_beacons(),
            params=self.__apply_context(params),
            error_msg="Reference was not replaced.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="replace reference on object"),
        )

    def __apply_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self._tenant is not None:
            params["tenant"] = self._tenant
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level.value
        return params

    def __apply_context_to_params_and_object(
        self, params: Dict[str, Any], obj: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if self._tenant is not None:
            obj["tenant"] = self._tenant
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level.value
        return params, obj

    def _serialize_props(self, props: Properties) -> Dict[str, Any]:
        return {key: self.__serialize_primitive(val) for key, val in props.items()}

    def _serialize_refs(self, refs: ReferenceInputs) -> Dict[str, Any]:
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
