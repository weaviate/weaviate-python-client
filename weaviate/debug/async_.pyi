from typing import Optional

from weaviate.connect.v4 import ConnectionAsync
from weaviate.classes.config import ConsistencyLevel
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
    ) -> Optional[DebugRESTObject]: ...
