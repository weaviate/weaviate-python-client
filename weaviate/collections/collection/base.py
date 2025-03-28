from typing import Generic, Optional
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.connect.v4 import ConnectionType
from weaviate.util import _capitalize_first_letter


class _CollectionBase(Generic[ConnectionType]):
    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        validate_arguments: bool,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
    ) -> None:
        self._connection = connection
        self.name = _capitalize_first_letter(name)
        self._validate_arguments = validate_arguments

        self.__tenant = tenant
        self.__consistency_level = consistency_level

    @property
    def tenant(self) -> Optional[str]:
        """The tenant of this collection object."""
        return self.__tenant

    @property
    def consistency_level(self) -> Optional[ConsistencyLevel]:
        """The consistency level of this collection object."""
        return self.__consistency_level
