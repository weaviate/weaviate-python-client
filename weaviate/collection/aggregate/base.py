from typing import Generic, Optional, Type

from weaviate.collection.classes.config import ConsistencyLevel
from weaviate.collection.classes.types import Properties
from weaviate.connect import Connection
from weaviate.gql.aggregate import AggregateBuilder


class _Aggregate(Generic[Properties]):
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        type_: Optional[Type[Properties]],
    ):
        self.__connection = connection
        self.__name = name
        self.__tenant = tenant
        self.__consistency_level = consistency_level
        self._type = type_

    def _query(self) -> AggregateBuilder:
        return AggregateBuilder(self.__name, self.__connection)
