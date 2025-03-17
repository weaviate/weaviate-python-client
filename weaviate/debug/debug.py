from typing import Awaitable, Dict, Generic, Optional, TypeVar, Union, overload

from httpx import Response

from weaviate.classes.config import ConsistencyLevel
from weaviate.connect.executor import execute, ExecutorResult, raise_exception
from weaviate.connect.v4 import ConnectionSync, ConnectionAsync, ConnectionType
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.debug.types import DebugRESTObject
from weaviate.types import UUID
from weaviate import syncify


class _DebugExecutor:
    def __init__(self) -> None:
        pass

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

class _DebugBase(Generic[ConnectionType]):
    _executor = _DebugExecutor()

    def __init__(self, connection: ConnectionType) -> None:
        self._connection = connection

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
        """Use the REST API endpoint /objects/{className}/{id} to retrieve an object directly from the database without search.

        The key difference between `debug.get_object_over_rest` and `query.fetch_object_by_id` is the underlying protocol.
        This method uses REST while that method uses gRPC.
        """
        result = self._executor.get_object_over_rest(
            collection=collection,
            uuid=uuid,
            consistency_level=consistency_level,
            node_name=node_name,
            tenant=tenant,
            connection=self._connection,
        )
        assert isinstance(result, Awaitable)
        return await result
