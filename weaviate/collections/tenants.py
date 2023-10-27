from typing import Dict, Any, List

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collections.classes.tenants import Tenant
from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException


class _Tenants:
    """Represents all the CRUD methods available on a collection's multi-tenancy specification within Weaviate.

    The collection must have been created with multi-tenancy enabled in order to use any of these methods. This class
    should not be instantiated directly, but is available as a property of the `Collection` class under
    the `collection.tenants` class attribute.
    """

    def __init__(self, connection: Connection, name: str) -> None:
        self.__connection = connection
        self.__name = name

    def create(self, tenants: List[Tenant]) -> None:
        """Create the specified tenants for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                List of tenants to add to the given collection.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeException`
                If Weaviate reports a non-OK status.
        """
        loaded_tenants = [tenant.model_dump() for tenant in tenants]

        path = "/schema/" + self.__name + "/tenants"
        try:
            response = self.__connection.post(path=path, weaviate_object=loaded_tenants)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                f"Collection tenants may not have been added properly for {self.__name}"
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException(
                f"Add collection tenants for {self.__name}", response
            )

    def remove(self, tenants: List[str]) -> None:
        """Remove the specified tenants from a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                List of tenant names to remove from the given class.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeException`
                If Weaviate reports a non-OK status.
        """
        path = "/schema/" + self.__name + "/tenants"
        try:
            response = self.__connection.delete(path=path, weaviate_object=tenants)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                f"Collection tenants may not have been deleted for {self.__name}"
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException(
                f"Delete collection tenants for {self.__name}", response
            )

    def get(self) -> Dict[str, Tenant]:
        """Return all tenants currently associated with a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeException`
                If Weaviate reports a non-OK status.
        """
        path = "/schema/" + self.__name + "/tenants"
        try:
            response = self.__connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                f"Could not get collection tenants for {self.__name}"
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException(
                f"Get collection tenants for {self.__name}", response
            )

        tenant_resp: List[Dict[str, Any]] = response.json()
        return {tenant["name"]: Tenant(**tenant) for tenant in tenant_resp}

    def update(self, tenants: List[Tenant]) -> None:
        """Update the specified tenants for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                List of tenants to update for the given collection.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeException`
                If Weaviate reports a non-OK status.
        """
        loaded_tenants = [tenant.model_dump() for tenant in tenants]

        path = "/schema/" + self.__name + "/tenants"
        try:
            response = self.__connection.put(path=path, weaviate_object=loaded_tenants)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                f"Collection tenants may not have been updated properly for {self.__name}"
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException(
                f"Update collection tenants for {self.__name}", response
            )
