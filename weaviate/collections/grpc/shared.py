from typing import Optional

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.connect import ConnectionV4
from weaviate.proto.v1 import base_pb2

PERMISSION_DENIED = "PERMISSION_DENIED"


class _BaseGRPC:
    def __init__(
        self,
        connection: ConnectionV4,
        consistency_level: Optional[ConsistencyLevel],
    ):
        self._connection = connection
        self._consistency_level = self._get_consistency_level(consistency_level)

    @staticmethod
    def _get_consistency_level(
        consistency_level: Optional[ConsistencyLevel],
    ) -> Optional["base_pb2.ConsistencyLevel"]:
        if consistency_level is None:
            return None

        if consistency_level.value == ConsistencyLevel.ONE:
            return base_pb2.ConsistencyLevel.CONSISTENCY_LEVEL_ONE
        elif consistency_level.value == ConsistencyLevel.QUORUM:
            return base_pb2.ConsistencyLevel.CONSISTENCY_LEVEL_QUORUM
        else:
            assert consistency_level.value == ConsistencyLevel.ALL
            return base_pb2.ConsistencyLevel.CONSISTENCY_LEVEL_ALL
