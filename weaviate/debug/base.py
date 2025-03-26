from abc import abstractmethod
from typing import Generic, Optional

from weaviate.classes.config import ConsistencyLevel
from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType
from weaviate.debug.executor import _DebugExecutor
from weaviate.debug.types import DebugRESTObject
from weaviate.types import UUID


class _DebugBase(Generic[ConnectionType]):
    _executor = _DebugExecutor()

    def __init__(self, connection: ConnectionType) -> None:
        self._connection: ConnectionType = connection

    @abstractmethod
    def get_object_over_rest(
        self,
        collection: str,
        uuid: UUID,
        *,
        consistency_level: Optional[ConsistencyLevel] = None,
        node_name: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> ExecutorResult[Optional[DebugRESTObject]]:
        """Use the REST API endpoint /objects/{className}/{id} to retrieve an object directly from the database without search.

        The key difference between `debug.get_object_over_rest` and `query.fetch_object_by_id` is the underlying protocol.
        This method uses REST while that method uses gRPC.
        """
        raise NotImplementedError()
