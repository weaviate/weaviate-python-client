from typing import List, Dict, Tuple, Optional

import grpc

from weaviate.connect import Connection
from weaviate.exceptions import WeaviateGRPCException
from weaviate_grpc import weaviate_pb2


class _BatchGRPC:
    def __init__(self, connection: Connection):
        self._connection: Connection = connection

    def batch(self, batch: List[weaviate_pb2.BatchObject]) -> Dict[int, str]:
        metadata: Optional[Tuple[Tuple[str, str]]] = None
        access_token = self._connection.get_current_bearer_token()
        if len(access_token) > 0:
            metadata = (("authorization", access_token),)
        try:
            assert self._connection.grpc_stub is not None
            res, _ = self._connection.grpc_stub.BatchObjects.with_call(
                weaviate_pb2.BatchObjectsRequest(
                    objects=batch,
                ),
                metadata=metadata,
            )

            objects: Dict[int, str] = {}
            for result in res.results:
                objects[result.index] = result.error
            return objects
        except grpc.RpcError as e:
            raise WeaviateGRPCException(e.details())
