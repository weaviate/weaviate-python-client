from typing import Generic, Optional, Type

from weaviate.collection.classes.config import CollectionConfigCreate
from weaviate.collection.classes.config import ConsistencyLevel
from weaviate.collection.classes.types import Properties, _check_data_model
from weaviate.collection.collection_base import CollectionBase
from weaviate.collection.config import _ConfigCollection
from weaviate.collection.data import _DataCollection
from weaviate.collection.grpc import _GrpcCollection
from weaviate.collection.tenants import _Tenants
from weaviate.connect import Connection
from weaviate.util import _capitalize_first_letter


class CollectionObject(Generic[Properties]):
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
        type_: Optional[Type[Properties]] = None,
    ) -> None:
        self._connection = connection
        self.name = name

        self.config = _ConfigCollection(self._connection, name)
        self.data = _DataCollection[Properties](connection, name, consistency_level, tenant, type_)
        self.query = _GrpcCollection(connection, name, consistency_level, tenant)
        self.tenants = _Tenants(connection, name)

        self.__tenant = tenant
        self.__consistency_level = consistency_level

    def with_tenant(self, tenant: Optional[str] = None) -> "CollectionObject":
        return CollectionObject(self._connection, self.name, self.__consistency_level, tenant)

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "CollectionObject":
        return CollectionObject(self._connection, self.name, consistency_level, self.__tenant)


class Collection(CollectionBase):
    def create(
        self, config: CollectionConfigCreate, data_model: Optional[Type[Properties]] = None
    ) -> CollectionObject[Properties]:
        name = super()._create(config)
        if config.name != name:
            raise ValueError(
                f"Name of created collection ({name}) does not match given name ({config.name})"
            )
        return self.get(name, data_model)

    def get(
        self, name: str, data_model: Optional[Type[Properties]] = None
    ) -> CollectionObject[Properties]:
        _check_data_model(data_model)
        name = _capitalize_first_letter(name)
        return CollectionObject[Properties](self._connection, name, type_=data_model)

    def delete(self, name: str) -> None:
        """Use this method to delete a collection from the Weaviate instance by its name.

        WARNING: If you have instances of client.collection.get() or client.collection.create()
        for this collection within your code, they will cease to function correctly after this operation.

        Parameters:
        - name: The name of the collection to delete.
        """
        self._delete(_capitalize_first_letter(name))

    def exists(self, name: str) -> bool:
        return self._exists(_capitalize_first_letter(name))
