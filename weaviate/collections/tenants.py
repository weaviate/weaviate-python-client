from typing import Dict, Any, List

from weaviate.collections.classes.tenants import Tenant
from weaviate.validator import _validate_input, _ValidateArgument
from weaviate.connect import ConnectionV4

from weaviate.connect.v4 import _ExpectedStatusCodes


class _Tenants:
    """Represents all the CRUD methods available on a collection's multi-tenancy specification within Weaviate.

    The collection must have been created with multi-tenancy enabled in order to use any of these methods. This class
    should not be instantiated directly, but is available as a property of the `Collection` class under
    the `collection.tenants` class attribute.
    """

    def __init__(self, connection: ConnectionV4, name: str) -> None:
        self.__connection = connection
        self.__name = name

    def create(self, tenants: List[Tenant]) -> None:
        """Create the specified tenants for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                List of tenants to add to the given collection.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
            `weaviate.WeaviateInvalidInputError`
                If `tenants` is not a list of `wvc.Tenant` objects.
        """
        _validate_input([_ValidateArgument(expected=[List[Tenant]], name="tenants", value=tenants)])

        loaded_tenants = [tenant.model_dump() for tenant in tenants]

        path = "/schema/" + self.__name + "/tenants"
        self.__connection.post(
            path=path,
            weaviate_object=loaded_tenants,
            error_msg=f"Collection tenants may not have been added properly for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Add collection tenants for {self.__name}"
            ),
        )

    def remove(self, tenants: List[str]) -> None:
        """Remove the specified tenants from a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                List of tenant names to remove from the given class.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
            `weaviate.WeaviateInvalidInputError`
                If `tenants` is not a list of strings.
        """
        _validate_input([_ValidateArgument(expected=[List[str]], name="tenants", value=tenants)])

        path = "/schema/" + self.__name + "/tenants"
        self.__connection.delete(
            path=path,
            weaviate_object=tenants,
            error_msg=f"Collection tenants may not have been deleted for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Delete collection tenants for {self.__name}"
            ),
        )

    def get(self) -> Dict[str, Tenant]:
        """Return all tenants currently associated with a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        path = "/schema/" + self.__name + "/tenants"
        response = self.__connection.get(
            path=path,
            error_msg=f"Could not get collection tenants for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Get collection tenants for {self.__name}"
            ),
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
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
            `weaviate.WeaviateInvalidInputError`
                If `tenants` is not a list of `wvc.Tenant` objects.
        """
        _validate_input([_ValidateArgument(expected=[List[Tenant]], name="tenants", value=tenants)])

        loaded_tenants = [tenant.model_dump() for tenant in tenants]

        path = "/schema/" + self.__name + "/tenants"
        self.__connection.put(
            path=path,
            weaviate_object=loaded_tenants,
            error_msg=f"Collection tenants may not have been updated properly for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Update collection tenants for {self.__name}"
            ),
        )
