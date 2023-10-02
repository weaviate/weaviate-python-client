from typing import List, Dict

import grpc  # type: ignore

from weaviate.collection.grpc_shared import _BaseGRPC
from weaviate.exceptions import WeaviateGRPCException
from weaviate_grpc import batch_pb2


class _BatchGRPC(_BaseGRPC):
    def batch(self, batch: List[batch_pb2.BatchObject]) -> Dict[int, str]:
        metadata = self._get_metadata()

        try:
            assert self._connection.grpc_stub is not None
            res, _ = self._connection.grpc_stub.BatchObjects.with_call(
                batch_pb2.BatchObjectsRequest(
                    objects=batch,
                    consistency_level=self._consistency_level,
                ),
                metadata=metadata,
            )

            objects: Dict[int, str] = {}
            for result in res.errors:
                objects[result.index] = result.error
            return objects
        except grpc.RpcError as e:
            raise WeaviateGRPCException(e.details())
