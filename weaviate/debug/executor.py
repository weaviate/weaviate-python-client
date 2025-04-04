from typing import Dict, Generic, Optional

from httpx import Response

from weaviate.classes.config import ConsistencyLevel
from weaviate.connect import executor
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionType
from weaviate.debug.types import DebugRESTObject
from weaviate.types import UUID


class _DebugExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def get_object_over_rest(
        self,
        collection: str,
        uuid: UUID,
        *,
        consistency_level: Optional[ConsistencyLevel] = None,
        node_name: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> executor.Result[Optional[DebugRESTObject]]:
        """Use the REST API endpoint /objects/{className}/{id} to retrieve an object directly from the database without search.

        The key difference between `debug.get_object_over_rest` and `query.fetch_object_by_id` is the underlying protocol.
        This method uses REST while that method uses gRPC.
        """
        path = f"/objects/{collection}/{str(uuid)}"

        params: Dict[str, str] = {}
        if consistency_level is not None:
            params["consistency"] = consistency_level.value
        if node_name is not None:
            params["node_name"] = node_name
        if tenant is not None:
            params["tenant"] = tenant

        def resp(response: Response) -> Optional[DebugRESTObject]:
            if response.status_code == 404:
                return None
            return DebugRESTObject(**response.json())

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            params=params,
            error_msg="Object was not retrieved",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="get object"),
        )
