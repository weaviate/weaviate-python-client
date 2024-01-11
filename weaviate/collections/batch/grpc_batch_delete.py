from typing import List, Optional, Union

import grpc  # type: ignore


from weaviate.collections.classes.batch import (
    _BatchDeleteObjects,
    _BatchDeleteResult,
    _BatchDeleteResultNoObjects,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.filters import _FilterToGRPC
from weaviate.collections.grpc.shared import _BaseGRPC
from weaviate.collections.queries.base import _WeaviateUUIDInt
from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateQueryException
from weaviate.proto.v1 import batch_delete_pb2


class _BatchDeleteGRPC(_BaseGRPC):
    """This class is used to insert multiple objects into Weaviate using the gRPC API.

    It is used within the `_Data` and `_Batch` classes hence the necessary generalities
    and abstractions so as not to couple to strongly to either use-case.
    """

    def __init__(self, connection: ConnectionV4, consistency_level: Optional[ConsistencyLevel]):
        super().__init__(connection, consistency_level, False)

    def batch_delete(
        self, name: str, filters: _Filters, verbose: bool, dry_run: bool, tenant: Optional[str]
    ) -> Union[_BatchDeleteResult, _BatchDeleteResultNoObjects]:
        metadata = self._get_metadata()
        try:
            assert self._connection.grpc_stub is not None
            res: batch_delete_pb2.BatchDeleteReply
            res, _ = self._connection.grpc_stub.BatchDelete.with_call(
                batch_delete_pb2.BatchDeleteRequest(
                    collection=name,
                    consistency_level=self._consistency_level,
                    verbose=verbose,
                    dry_run=dry_run,
                    tenant=tenant,
                    filters=_FilterToGRPC.convert(filters, self._connection._weaviate_version),
                ),
                metadata=metadata,
            )

            if verbose:
                objects: List[_BatchDeleteObjects] = [
                    _BatchDeleteObjects(
                        uuid=_WeaviateUUIDInt(int.from_bytes(obj.uuid, byteorder="big")),
                        successful=obj.successful,
                        error=obj.error if obj.error != "" else None,
                    )
                    for obj in res.objects
                ]
                return _BatchDeleteResult(
                    failed=res.failed,
                    successful=res.successful,
                    matches=res.matches,
                    objects=objects,
                )
            else:
                return _BatchDeleteResultNoObjects(
                    failed=res.failed, successful=res.successful, matches=res.matches
                )

        except grpc.RpcError as e:
            raise WeaviateQueryException(e.details())
