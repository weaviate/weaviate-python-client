import uuid as uuid_package
from dataclasses import dataclass
from typing import Type, Tuple, Optional, Any, List, Dict, Generic

from pydantic import create_model
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collection.collection_base import CollectionBase, CollectionObjectBase
from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.weaviate_types import (
    CollectionConfigModel,
    BaseProperty,
    PYTHON_TYPE_TO_DATATYPE,
    UUID,
    Metadata,
    MetadataReturn,
    Model,
)


@dataclass
class _Object(Generic[Model]):
    data: Model
    metadata: MetadataReturn


class CollectionObjectModel(CollectionObjectBase):
    def __init__(self, connection: Connection, name: str, dynamic_model: Type[Model]) -> None:
        super().__init__(connection, name)
        self._model = dynamic_model

    def insert(self, obj: Model) -> uuid_package.UUID:
        self._model.model_validate(obj)

        weaviate_obj: Dict[str, Any] = {
            "class": self._name,
            "properties": obj.model_dump(exclude={"uuid", "vector"}),
            "id": obj.uuid,
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self._insert(weaviate_obj)
        return uuid_package.UUID(str(obj.uuid))

    def get_by_id(self, uuid: UUID, metadata: Optional[Metadata] = None) -> Optional[_Object]:
        ret = self._get_by_id(uuid=uuid, metadata=metadata)
        if ret is None:
            return None
        return self._json_to_object(ret)

    def get(self, metadata: Optional[Metadata] = None) -> Optional[List[_Object]]:
        ret = self._get(metadata=metadata)
        if ret is None:
            return None

        return [self._json_to_object(obj) for obj in ret["objects"]]

    def _json_to_object(self, obj: Dict[str, Any]) -> _Object:
        return _Object(data=self._model(**obj["properties"]), metadata=MetadataReturn(**obj))


class CollectionModel(CollectionBase):
    def create(self, config: CollectionConfigModel) -> CollectionObjectModel:
        super()._create(config)

        return CollectionObjectModel(self._connection, config.name, config.properties)

    def get(self, collection_name: str, model: Type[Model]) -> CollectionObjectModel:
        path = f"/schema/{collection_name.capitalize()}"

        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Schema could not be retrieved.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Get schema", response)

        response_json = response.json()
        model_props = model.type_to_dict(model)
        schema_props = [
            {"name": prop["name"], "dataType": prop["dataType"]}
            for prop in response_json["properties"]
        ]

        def compare(s: List[Any], t: List[Any]) -> bool:
            t = list(t)  # make a mutable copy
            try:
                for elem in s:
                    t.remove(elem)
            except ValueError:
                return False
            return not t

        if compare(model_props, schema_props):
            raise TypeError("Schemas not compatible")
        return CollectionObjectModel(self._connection, collection_name, model)

    def get_dynamic(self, collection_name: str) -> Tuple[CollectionObjectModel, Type[BaseProperty]]:
        path = f"/schema/{collection_name.capitalize()}"

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

        return CollectionObjectModel(self._connection, collection_name, model), model
