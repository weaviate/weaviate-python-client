from typing import Optional

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.grpc.tenants import _TenantsGRPC
from weaviate.connect import ConnectionV4


class _TenantsBase:
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        consistency_level: Optional[ConsistencyLevel] = None,
        validate_arguments: bool = True,
    ) -> None:
        self._connection = connection
        self._name = name
        self._grpc = _TenantsGRPC(
            connection=connection,
            name=name,
            consistency_level=consistency_level,
        )
        self._validate_arguments = validate_arguments
