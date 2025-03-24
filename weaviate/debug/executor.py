from typing import Dict, Optional, Union

from httpx import Response

from weaviate.classes.config import ConsistencyLevel
from weaviate.connect.executor import execute, ExecutorResult, raise_exception
from weaviate.connect.v4 import ConnectionSync, ConnectionAsync
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.debug.types import DebugRESTObject
from weaviate.types import UUID


class _DebugExecutor:
    def get_object_over_rest(
        self,
        collection: str,
        uuid: UUID,
        *,
        connection: Union[ConnectionAsync, ConnectionSync],
        consistency_level: Optional[ConsistencyLevel] = None,
        node_name: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> ExecutorResult[Optional[DebugRESTObject]]:
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

        return execute(
            response_callback=resp,
            exception_callback=raise_exception,
            method=connection.get,
            path=path,
            params=params,
            error_msg="Object was not retrieved",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="get object"),
        )
