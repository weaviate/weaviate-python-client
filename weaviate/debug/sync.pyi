from typing import Optional

from weaviate.classes.config import ConsistencyLevel
from weaviate.debug.debug import _DebugBase
from weaviate.debug.types import DebugRESTObject
from weaviate.types import UUID

class _Debug(_DebugBase):
    def get_object(
        self,
        collection: str,
        uuid: UUID,
        *,
        consistency_level: Optional[ConsistencyLevel] = None,
        nodename: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> Optional[DebugRESTObject]: ...
