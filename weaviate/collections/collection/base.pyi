from typing import Generic, Literal, Optional, Type, TypeVar, Union, overload
from weaviate.connect import ConnectionV4
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES
from weaviate.collections.classes.internal import (
    CrossReferences,
    References,
    ReturnProperties,
    ReturnReferences,
    TReferences,
)
from weaviate.collections.cluster import _ClusterAsync
from weaviate.collections.config import _ConfigCollectionAsync
from weaviate.collections.query import _QueryCollectionAsync
from weaviate.collections.classes.types import Properties, TProperties
from weaviate.types import UUID

Collection = TypeVar("Collection", bound="_CollectionBase")

class _CollectionBase(Generic[Properties, References]):
    name: str

    _connection: ConnectionV4
    _config: _ConfigCollectionAsync
    _validate_arguments: bool
    _query: _QueryCollectionAsync[Properties, References]

    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        validate_arguments: bool,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
        properties: Optional[Type[Properties]] = None,
        references: Optional[Type[References]] = None,
    ) -> None: ...
    def with_tenant(self: Collection, tenant: Optional[Union[str, Tenant]] = None) -> Collection:
        """Use this method to return a collection object specific to a single tenant.

        If multi-tenancy is not configured for this collection then Weaviate will throw an error.

        This method does not send a request to Weaviate. It only returns a new collection object that is specific
        to the tenant you specify.

        Arguments:
            `tenant`
                The tenant to use. Can be `str` or `wvc.tenants.Tenant`.
        """
        ...

    def with_consistency_level(
        self: Collection, consistency_level: Optional[ConsistencyLevel] = None
    ) -> Collection:
        """Use this method to return a collection object specific to a single consistency level.

        If replication is not configured for this collection then Weaviate will throw an error.

        This method does not send a request to Weaviate. It only returns a new collection object that is specific
        to the consistency level you specify.

        Arguments:
            `consistency_level`
                The consistency level to use.
        """
        ...

    @property
    def tenant(self) -> Optional[str]:
        """The tenant of this collection object."""
        ...

    @property
    def consistency_level(self) -> Optional[ConsistencyLevel]:
        """The consistency level of this collection object."""
        ...
