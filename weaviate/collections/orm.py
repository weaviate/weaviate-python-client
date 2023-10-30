from typing import Type, Optional, Any, Dict, Generic, Tuple

from pydantic import create_model
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collections.base import _CollectionBase, _CollectionsBase
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.orm import (
    BaseProperty,
    CollectionModelConfig,
    Model,
    UserModelType,
)
from weaviate.collections.config import _ConfigCollectionModel
from weaviate.collections.data import _DataCollectionModel
from weaviate.collections.query import _GrpcCollectionModel
from weaviate.collections.tenants import _Tenants
from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.util import _capitalize_first_letter
from weaviate.types import PYTHON_TYPE_TO_DATATYPE


class _CollectionObjectModel(_CollectionBase, Generic[Model]):
    def __init__(
        self,
        connection: Connection,
        name: str,
        model: Type[Model],
        config: _ConfigCollectionModel,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
    ) -> None:
        super().__init__(name)

        self._connection = connection

        self.config = config
        self.data = _DataCollectionModel[Model](
            connection, self.name, model, consistency_level, tenant
        )
        self.query = _GrpcCollectionModel[Model](
            connection, self.name, model, tenant, consistency_level
        )
        self.tenants = _Tenants(connection, self.name)

        self.__consistency_level = consistency_level
        self.__model: Type[Model] = model
        self.__tenant = tenant

    @property
    def model(self) -> Type[Model]:
        return self.__model

    def with_tenant(self, tenant: Optional[str] = None) -> "_CollectionObjectModel[Model]":
        return _CollectionObjectModel[Model](
            self._connection, self.name, self.__model, self.config, self.__consistency_level, tenant
        )

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "_CollectionObjectModel[Model]":
        return _CollectionObjectModel[Model](
            self._connection, self.name, self.__model, self.config, consistency_level, self.__tenant
        )


class _CollectionModel(_CollectionsBase):
    def create(self, config: CollectionModelConfig[Model]) -> _CollectionObjectModel[Model]:
        name = super()._create(config)
        config_name = _capitalize_first_letter(config.model.__name__)
        if config_name != name:
            raise ValueError(
                f"Name of created collection ({name}) does not match given name ({config_name})"
            )
        return self.get(config.model)

    def get(self, model: Type[Model]) -> _CollectionObjectModel[Model]:
        name = _capitalize_first_letter(model.__name__)
        config = _ConfigCollectionModel(self._connection, name, None)
        if config.is_invalid(model):
            raise TypeError(
                f"Model {model.__name__} definition does not match collection {name} config"
            )
        return _CollectionObjectModel[Model](self._connection, name, model, config)

    def get_dynamic(self, name: str) -> Tuple[_CollectionObjectModel[BaseProperty], UserModelType]:
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
        config = _ConfigCollectionModel(self._connection, name, None)
        return _CollectionObjectModel[BaseProperty](self._connection, name, model, config), model

    def delete(self, model: Type[Model]) -> None:
        """Use this method to delete a collection from the Weaviate instance by its ORM model.

        WARNING: If you have instances of client.orm.get() or client.orm.create()
        for this collection within your code, they will cease to function correctly after this operation.

        Parameters:
            - model: The ORM model of the collection to be deleted.
        """
        name = _capitalize_first_letter(model.__name__)
        return self._delete(name)

    def exists(self, model: Type[Model]) -> bool:
        name = _capitalize_first_letter(model.__name__)
        return self._exists(name)

    def update(self, model: Type[Model]) -> _CollectionObjectModel[Model]:
        name = _capitalize_first_letter(model.__name__)
        config = _ConfigCollectionModel(self._connection, name, None)
        config.update_model(model)
        return _CollectionObjectModel[Model](self._connection, name, model, config)
