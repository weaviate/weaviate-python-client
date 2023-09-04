from typing import Type, Optional, Any, Dict, Generic, Tuple

from pydantic import create_model
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collection.classes.orm import (
    BaseProperty,
    CollectionModelConfig,
    Model,
    UserModelType,
)
from weaviate.collection.collection_base import CollectionBase
from weaviate.collection.config import _ConfigCollectionModel
from weaviate.collection.data import _DataCollectionModel
from weaviate.collection.grpc import _GrpcCollectionModel
from weaviate.collection.tenants import _Tenants
from weaviate.connect import Connection
from weaviate.data.replication import ConsistencyLevel
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.util import _capitalize_first_letter
from weaviate.weaviate_types import PYTHON_TYPE_TO_DATATYPE


class CollectionObjectModel(Generic[Model]):
    def __init__(
        self,
        connection: Connection,
        name: str,
        model: Type[Model],
        config: _ConfigCollectionModel,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
    ) -> None:
        self._connection = connection
        self.name = name

        self.config = config
        self.data = _DataCollectionModel[Model](connection, name, model, consistency_level, tenant)
        self.query = _GrpcCollectionModel[Model](connection, name, model, tenant)
        self.tenants = _Tenants(connection, name)

        self.__consistency_level = consistency_level
        self.__model: Type[Model] = model
        self.__tenant = tenant

    @property
    def model(self) -> Type[Model]:
        return self.__model

    def with_tenant(self, tenant: Optional[str] = None) -> "CollectionObjectModel[Model]":
        return CollectionObjectModel[Model](
            self._connection, self.name, self.__model, self.config, self.__consistency_level, tenant
        )

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "CollectionObjectModel[Model]":
        return CollectionObjectModel[Model](
            self._connection, self.name, self.__model, self.config, consistency_level, self.__tenant
        )


class CollectionModel(CollectionBase):
    def __init__(self, connection: Connection):
        super().__init__(connection)

    def create(self, config: CollectionModelConfig[Model]) -> CollectionObjectModel[Model]:
        name = super()._create(config)
        config_name = _capitalize_first_letter(config.model.__name__)
        if config_name != name:
            raise ValueError(
                f"Name of created collection ({name}) does not match given name ({config_name})"
            )
        return self.get(config.model)

    def get(self, model: Type[Model]) -> CollectionObjectModel[Model]:
        name = _capitalize_first_letter(model.__name__)
        config = _ConfigCollectionModel(self._connection, name)
        if config.is_invalid(model):
            raise TypeError(
                f"Model {model.__name__} definition does not match collection {name} config"
            )
        return CollectionObjectModel[Model](self._connection, name, model, config)

    def get_dynamic(self, name: str) -> Tuple[CollectionObjectModel[BaseProperty], UserModelType]:
        path = f"/schema/{_capitalize_first_letter(name)}"

        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Schema could not be retrieved.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Get schema", response)

        response_json = response.json()
        fields: Dict[str, Any] = {
            prop["name"]: (PYTHON_TYPE_TO_DATATYPE[prop["dataType"][0]], None)
            for prop in response_json["properties"]
        }
        model = create_model(response_json["class"], **fields, __base__=BaseProperty)
        config = _ConfigCollectionModel(self._connection, name)
        return CollectionObjectModel[BaseProperty](self._connection, name, model, config), model

    def delete(self, model: Type[Model]) -> None:
        """Use this method to delete a collection from the Weaviate instance by its ORM model.

        WARNING: If you have instances of client.collection_model.get() or client.collection_model.create()
        for this collection within your code, they will cease to function correctly after this operation.

        Parameters:
        - model: The ORM model of the collection to be deleted.
        """
        name = _capitalize_first_letter(model.__name__)
        return self._delete(name)

    def exists(self, model: Type[Model]) -> bool:
        name = _capitalize_first_letter(model.__name__)
        return self._exists(name)

    def update(self, model: Type[Model]) -> CollectionObjectModel[Model]:
        name = _capitalize_first_letter(model.__name__)
        config = _ConfigCollectionModel(self._connection, name)
        config.update_model(model)
        return CollectionObjectModel[Model](self._connection, name, model, config)
