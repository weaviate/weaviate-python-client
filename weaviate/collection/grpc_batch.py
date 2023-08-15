from typing import List

from weaviate.collection import grpc
from weaviate.connect import Connection
from weaviate.exceptions import WeaviateGRPCException
from weaviate_grpc import weaviate_pb2


class _BatchGRPC:
    def __init__(self, connection: Connection):
        self._connection: Connection = connection

    def batch(self, batch: List[weaviate_pb2.BatchObject]):
        metadata = ()
        access_token = self._connection.get_current_bearer_token()
        if len(access_token) > 0:
            metadata = (("authorization", access_token),)
        try:
            res, _ = self._connection.grpc_stub.BatchObjects.with_call(
                weaviate_pb2.BatchObjectsRequest(
                    objects=batch,
                ),
                metadata=metadata,
            )
        except grpc.RpcError as e:
            raise WeaviateGRPCException(e.details())
