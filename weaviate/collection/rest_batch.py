from typing import Optional

from weaviate.collection.classes.config import ConsistencyLevel
from weaviate.collection.classes.filters import _Filters
from weaviate.connect import Connection


class _BatchREST:
    def __init__(
        self, connection: Connection, consistency_level: Optional[ConsistencyLevel]
    ) -> None:
        self.__connection = connection
        self.__consistency_level = consistency_level

    def delete(
        self, class_name: str, where: _Filters, verbose: bool = False, dry_run: bool = False
    ) -> None:
        pass
