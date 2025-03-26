from typing import Optional

from weaviate.classes.config import ConsistencyLevel
from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionAsync
from weaviate.debug.base import _DebugBase
from weaviate.debug.types import DebugRESTObject
from weaviate.types import UUID


class _DebugAsync(_DebugBase[ConnectionAsync]):
    async def get_object_over_rest(
        self,
        collection: str,
        uuid: UUID,
        *,
        consistency_level: Optional[ConsistencyLevel] = None,
        node_name: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> Optional[DebugRESTObject]:
        return await aresult(
            self._executor.get_object_over_rest(
                collection=collection,
                uuid=uuid,
                consistency_level=consistency_level,
                node_name=node_name,
                tenant=tenant,
                connection=self._connection,
            )
        )
