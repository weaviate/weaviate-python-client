from typing import List, Optional, Union

from weaviate.collections.classes.batch import (
    DeleteManyObject,
    DeleteManyReturn,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.filters import _FilterToGRPC
from weaviate.collections.grpc.shared import _BaseGRPC
from weaviate.connect import executor
from weaviate.connect.v4 import Connection
from weaviate.proto.v1 import batch_delete_pb2
from weaviate.util import _ServerVersion, _WeaviateUUIDInt


class _BatchDeleteGRPC(_BaseGRPC):
    """This class is used to delete multiple objects from Weaviate using the gRPC API."""

    def __init__(
        self, weaviate_version: _ServerVersion, consistency_level: Optional[ConsistencyLevel]
    ):
        super().__init__(weaviate_version, consistency_level, False)

    def batch_delete(
        self,
        connection: Connection,
        *,
        name: str,
        filters: _Filters,
        verbose: bool,
        dry_run: bool,
        tenant: Optional[str]
    ) -> executor.Result[Union[DeleteManyReturn[List[DeleteManyObject]], DeleteManyReturn[None]]]:
        def resp(
            res: batch_delete_pb2.BatchDeleteReply,
        ) -> Union[DeleteManyReturn[List[DeleteManyObject]], DeleteManyReturn[None]]:
            if verbose:
                objects: List[DeleteManyObject] = [
                    DeleteManyObject(
                        uuid=_WeaviateUUIDInt(int.from_bytes(obj.uuid, byteorder="big")),
                        successful=obj.successful,
                        error=obj.error if obj.error != "" else None,
                    )
                    for obj in res.objects
                ]
                return DeleteManyReturn(
                    failed=res.failed,
                    successful=res.successful,
                    matches=res.matches,
                    objects=objects,
                )
            else:
                return DeleteManyReturn(
                    failed=res.failed, successful=res.successful, matches=res.matches, objects=None
                )

        request = batch_delete_pb2.BatchDeleteRequest(
            collection=name,
            consistency_level=self._consistency_level,
            verbose=verbose,
            dry_run=dry_run,
            tenant=tenant,
            filters=_FilterToGRPC.convert(filters),
        )
        return executor.execute(
            response_callback=resp,
            method=connection.grpc_batch_delete,
            request=request,
        )
