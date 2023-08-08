from copy import copy
from typing import Dict, Any, Optional, List, Tuple, Union, TypeVar

import uuid as uuid_package
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collection.classes import (
    CollectionConfigBase,
    Error,
    Errors,
    MetadataGet,
    Tenant,
    UUID,
)
from weaviate.connect import Connection
from weaviate.data.replication import ConsistencyLevel
from weaviate.exceptions import UnexpectedStatusCodeException, ObjectAlreadyExistsException
from weaviate.util import _to_beacons, _capitalize_first_letter
from weaviate.weaviate_types import UUIDS


class _Tenants:
    """
    Represents all the CRUD methods available on a collection's multi-tenancy specification within Weaviate. The
    collection must have been created with multi-tenancy enabled in order to use any of these methods. This class
    should not be instantiated directly, but is available as a property of the `Collection` class under
    the `collection.tenants` class attribute.
    """

    def __init__(self, connection: Connection, name: str) -> None:
        self._connection = connection
        self.name = name

    def add(self, tenants: List[Tenant]) -> None:
        """Add the specified tenants to a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Parameters:
        - `tenants`: List of Tenants.

        Raises:
        - `requests.ConnectionError`
            - If the network connection to Weaviate fails.
        - `weaviate.UnexpectedStatusCodeException`
            - If Weaviate reports a non-OK status.
        """

        loaded_tenants = [{"name": tenant.name} for tenant in tenants]

        path = "/schema/" + self.name + "/tenants"
        try:
            response = self._connection.post(path=path, weaviate_object=loaded_tenants)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                f"Collection tenants may not have been added properly for {self.name}"
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException(f"Add collection tenants for {self.name}", response)

    def remove(self, tenants: List[str]) -> None:
        """Remove the specified tenants from a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Parameters:
        - `tenants`: List of tenant names to remove from the given class.

        Raises:
        - `TypeError`
            - If 'tenants' has not the correct type.
        - `requests.ConnectionError`
            - If the network connection to Weaviate fails.
        - `weaviate.UnexpectedStatusCodeException`
            - If Weaviate reports a non-OK status.
        """
        path = "/schema/" + self.name + "/tenants"
        try:
            response = self._connection.delete(path=path, weaviate_object=tenants)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                f"Collection tenants may not have been deleted for {self.name}"
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException(
                f"Delete collection tenants for {self.name}", response
            )

    def get(self) -> List[Tenant]:
        """Return all tenants currently associated with a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Raises:
        - `requests.ConnectionError`
            - If the network connection to Weaviate fails.
        - `weaviate.UnexpectedStatusCodeException`
            - If Weaviate reports a non-OK status.
        """
        path = "/schema/" + self.name + "/tenants"
        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                f"Could not get collection tenants for {self.name}"
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException(f"Get collection tenants for {self.name}", response)

        tenant_resp: List[Dict[str, Any]] = response.json()
        return [Tenant(**tenant) for tenant in tenant_resp]


T = TypeVar("T", bound="CollectionObjectBase")


class CollectionObjectBase:
    def __init__(self, connection: Connection, name: str) -> None:
        self.tenants = _Tenants(connection, name)
        self._connection = connection
        self.__name = name
        self.__tenant: Optional[str] = None
        self._consistency_level: Optional[str] = None

    @property
    def tenant(self) -> Optional[str]:
        return self.__tenant

    @property
    def name(self) -> str:
        return self.__name

    def _with_tenant(self: T, tenant: Optional[str] = None) -> T:
        new = copy(self)
        new.__tenant = tenant
        return new

    def _with_consistency_level(self: T, consistency_level: Optional[ConsistencyLevel] = None) -> T:
        new = copy(self)
        new._consistency_level = (
            ConsistencyLevel(consistency_level).value if consistency_level is not None else None
        )
        return new

    def _insert(self, weaviate_obj: Dict[str, Any]) -> uuid_package.UUID:
        path = "/objects"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)
        try:
            response = self._connection.post(path=path, weaviate_object=weaviate_obj, params=params)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not added to Weaviate.") from conn_err
        if response.status_code == 200:
            return uuid_package.UUID(weaviate_obj["id"])

        try:
            if "already exists" in response.json()["error"][0]["message"]:
                raise ObjectAlreadyExistsException(weaviate_obj["id"])
        except KeyError:
            pass
        raise UnexpectedStatusCodeException("Creating object", response)

    def _insert_many(self, objects: List[Dict[str, Any]]) -> List[Union[uuid_package.UUID, Errors]]:
        params: Dict[str, str] = {}
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level

        if self.__tenant is not None:
            for obj in objects:
                obj["tenant"] = self.__tenant

        response = self._connection.post(
            path="/batch/objects",
            weaviate_object={"fields": ["ALL"], "objects": objects},
            params=params,
        )
        if response.status_code == 200:
            results = response.json()
            return [
                [Error(message=err) for err in result["result"]["errors"]["error"]]
                if "result" in result
                and "errors" in result["result"]
                and "error" in result["result"]["errors"]
                else objects[i]["id"]
                for i, result in enumerate(results)
            ]

        raise UnexpectedStatusCodeException("Send object batch", response)

    def delete(self, uuid: UUID) -> bool:
        path = f"/objects/{self.name}/{uuid}"

        try:
            response = self._connection.delete(path=path, params=self.__apply_context({}))
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object could not be deleted.") from conn_err
        if response.status_code == 204:
            return True  # Successfully deleted
        elif response.status_code == 404:
            return False  # did not exist
        raise UnexpectedStatusCodeException("Delete object", response)

    def _replace(self, weaviate_obj: Dict[str, Any], uuid: UUID) -> None:
        path = f"/objects/{self.name}/{uuid}"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)

        weaviate_obj["id"] = str(uuid)  # must add ID to payload for PUT request

        try:
            response = self._connection.put(path=path, weaviate_object=weaviate_obj, params=params)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not replaced.") from conn_err
        if response.status_code == 200:
            return
        raise UnexpectedStatusCodeException("Replacing object", response)

    def _update(self, weaviate_obj: Dict[str, Any], uuid: UUID) -> None:
        path = f"/objects/{self.name}/{uuid}"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)

        try:
            response = self._connection.patch(
                path=path, weaviate_object=weaviate_obj, params=params
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not updated.") from conn_err
        if response.status_code == 204:
            return
        raise UnexpectedStatusCodeException("Update object", response)

    def _get_by_id(
        self, uuid: UUID, metadata: Optional[MetadataGet] = None
    ) -> Optional[Dict[str, Any]]:
        path = f"/objects/{self.name}/{uuid}"

        return self._get_from_weaviate(
            params=self.__apply_context({}), path=path, metadata=metadata
        )

    def _get(self, metadata: Optional[MetadataGet] = None) -> Optional[Dict[str, Any]]:
        path = "/objects"
        params: Dict[str, Any] = {"class": self.name}

        return self._get_from_weaviate(
            params=self.__apply_context(params), path=path, metadata=metadata
        )

    def _get_from_weaviate(
        self, params: Dict[str, Any], path: str, metadata: Optional[MetadataGet] = None
    ) -> Optional[Dict[str, Any]]:
        include = ""
        if metadata is not None:
            include += metadata.to_rest()

        if len(include) > 0:
            params["include"] = include

        try:
            response = self._connection.get(path=path, params=params)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Could not get object/s.") from conn_err
        if response.status_code == 200:
            return_dict: Dict[str, Any] = response.json()
            return return_dict
        if response.status_code == 404:
            return None
        raise UnexpectedStatusCodeException("Get object/s", response)

    def _reference_add(self, from_uuid: UUID, from_property_name: str, to_uuids: UUIDS) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property_name}"
        beacons = _to_beacons(to_uuids)
        for beacon in beacons:
            try:
                response = self._connection.post(
                    path=path,
                    weaviate_object=beacon,
                    params=self.__apply_context(params),
                )
            except RequestsConnectionError as conn_err:
                raise RequestsConnectionError("Reference was not added.") from conn_err
            if response.status_code != 200:
                raise UnexpectedStatusCodeException("Add property reference to object", response)

    def _reference_add_many(self, refs: List[Dict[str, str]]) -> None:
        params: Dict[str, str] = {}
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level

        if self.__tenant is not None:
            for ref in refs:
                ref["tenant"] = self.__tenant

        response = self._connection.post(
            path="/batch/references", weaviate_object=refs, params=params
        )
        if response.status_code == 200:
            return None
        raise UnexpectedStatusCodeException("Send ref batch", response)

    def _reference_delete(self, from_uuid: UUID, from_property_name: str, to_uuids: UUIDS) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property_name}"
        beacons = _to_beacons(to_uuids)
        for beacon in beacons:
            try:
                response = self._connection.delete(
                    path=path,
                    weaviate_object=beacon,
                    params=self.__apply_context(params),
                )
            except RequestsConnectionError as conn_err:
                raise RequestsConnectionError("Reference was not added.") from conn_err
            if response.status_code != 204:
                raise UnexpectedStatusCodeException("Add property reference to object", response)

    def _reference_replace(self, from_uuid: UUID, from_property_name: str, to_uuids: UUIDS) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property_name}"
        try:
            response = self._connection.put(
                path=path,
                weaviate_object=_to_beacons(to_uuids),
                params=self.__apply_context(params),
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Reference was not added.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Add property reference to object", response)

    def __apply_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self.__tenant is not None:
            params["tenant"] = self.__tenant
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level
        return params

    def __apply_context_to_params_and_object(
        self, params: Dict[str, Any], obj: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if self.__tenant is not None:
            obj["tenant"] = self.__tenant
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level
        return params, obj


class CollectionBase:
    def __init__(self, connection: Connection):
        self._connection = connection

    def _create(
        self,
        config: CollectionConfigBase,
    ) -> str:
        weaviate_object = config.to_dict()

        try:
            response = self._connection.post(path="/schema", weaviate_object=weaviate_object)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Class may not have been created properly.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Create class", response)

        collection_name = response.json()["class"]
        assert isinstance(collection_name, str)
        return collection_name

    def _exists(self, name: str) -> bool:
        path = f"/schema/{_capitalize_first_letter(name)}"
        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Existenz of class.") from conn_err

        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        raise UnexpectedStatusCodeException("collection exists", response)

    def _delete(self, name: str) -> None:
        path = f"/schema/{_capitalize_first_letter(name)}"
        try:
            response = self._connection.delete(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Deletion of class.") from conn_err
        if response.status_code == 200:
            return

        UnexpectedStatusCodeException("Delete collection", response)
