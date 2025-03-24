from typing import Generic, Optional, TypeVar
from weaviate.connect.v4 import ConnectionType
from weaviate.collections.classes.config import ConsistencyLevel

Collection = TypeVar("Collection", bound="_CollectionBase")

class _CollectionBase(Generic[ConnectionType]):
    name: str
    _connection: ConnectionType
    _validate_arguments: bool

    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        validate_arguments: bool,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
    ) -> None: ...
    @property
    def tenant(self) -> Optional[str]:
        """The tenant of this collection object."""
        ...

    @property
    def consistency_level(self) -> Optional[ConsistencyLevel]:
        """The consistency level of this collection object."""
        ...
