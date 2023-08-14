from typing import Optional

from weaviate.collection.classes import CollectionConfig
from weaviate.collection.config import _ConfigCollection
from weaviate.collection.collection_base import CollectionBase
from weaviate.collection.data import _DataCollection
from weaviate.collection.grpc import _GrpcCollection
from weaviate.collection.tenants import _Tenants
from weaviate.connect import Connection
from weaviate.data.replication import ConsistencyLevel


class CollectionObject:
    def __init__(
        self,
        connection: Connection,
        name: str,
        config: _ConfigCollection,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
    ) -> None:
        self._connection = connection
        self.name = name

        self.config = config
        self.data = _DataCollection(connection, name, config, consistency_level, tenant)
        self.query = _GrpcCollection(connection, name, tenant)
        self.tenants = _Tenants(connection, name)

        self.__tenant = tenant
        self.__consistency_level = consistency_level

    def with_tenant(self, tenant: Optional[str] = None) -> "CollectionObject":
        return CollectionObject(
            self._connection, self.name, self.config, self.__consistency_level, tenant
        )

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "CollectionObject":
        return CollectionObject(
            self._connection, self.name, self.config, consistency_level, self.__tenant
        )


class Collection(CollectionBase):
    def create(self, config: CollectionConfig, debug_mode: bool = False) -> CollectionObject:
        name = super()._create(config)
        if config.name != name:
            raise ValueError(
                f"Name of created collection ({name}) does not match given name ({config.name})"
            )
        return self.get(name, debug_mode)

    def get(self, name: str, debug_mode: bool = False) -> CollectionObject:
        config = _ConfigCollection.make(self._connection, name, debug_mode)
        return CollectionObject(self._connection, name, config)

    def delete(self, name: str) -> None:
        """Use this method to delete a collection from the Weaviate instance by its name.

        WARNING: If you have instances of client.collection_model.get() or client.collection_model.create()
        for this collection within your code, they will be cease to function correctly after this operation.

        Parameters:
        - name: The name of the collection to delete.
        """
        self._delete(name)

    def exists(self, name: str) -> bool:
        return self._exists(name)
