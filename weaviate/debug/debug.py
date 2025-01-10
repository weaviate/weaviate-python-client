from typing import Dict, Optional

from weaviate.classes.config import ConsistencyLevel
from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.debug.types import DebugObject
from weaviate.types import UUID


class _DebugBase:
    def __init__(
        self,
        connection: ConnectionV4,
    ) -> None:
        self._connection = connection


class _DebugAsync(_DebugBase):
    async def get_object(
        self,
        collection: str,
        uuid: UUID,
        *,
        consistency_level: Optional[ConsistencyLevel] = None,
        nodename: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> Optional[DebugObject]:
        path = f"/objects/{collection}/{str(uuid)}"

        params: Dict[str, str] = {}
        if consistency_level is not None:
            params["consistency"] = consistency_level.value
        if nodename is not None:
            params["nodename"] = nodename
        if tenant is not None:
            params["tenant"] = tenant

        res = await self._connection.get(
            path=path,
            params=params,
            error_msg="Object was not retrieved",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="get object"),
        )
        if res.status_code == 404:
            return None
        return DebugObject(**res.json())
