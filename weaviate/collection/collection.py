import uuid
from typing import Type, Tuple, Optional, Any, List, Dict

from pydantic import create_model
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException, ObjectAlreadyExistsException
from weaviate.weaviate_types import CollectionConfig, BaseProperty, PYTHON_TYPE_TO_DATATYPE


class CollectionObject:
    def __init__(
        self, connection: Connection, name: str, dynamic_model: Optional[Type[BaseProperty]]
    ) -> None:
        self._connection = connection
        self._model = dynamic_model
        self._name = name

    def insert(self, obj: BaseProperty) -> uuid.UUID:
        if self._model is not None:
            self._model.model_validate(obj)

        weaviate_obj = {
            "class": self._name,
            "properties": obj.model_dump(exclude={"uuid", "vector"}),
            "id": obj.uuid,
        }

        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        path = "/objects"
        try:
            response = self._connection.post(path=path, weaviate_object=weaviate_obj, params={})
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not added to Weaviate.") from conn_err
        if response.status_code == 200:
            return weaviate_obj["id"]

        try:
            if "already exists" in response.json()["error"][0]["message"]:
                raise ObjectAlreadyExistsException(str(uuid))
        except KeyError:
            raise UnexpectedStatusCodeException("Creating object", response)


class Collection:
    def __init__(self, connection: Connection):
        self._connection = connection

    def create(self, model: CollectionConfig) -> CollectionObject:
        try:
            response = self._connection.post(path="/schema", weaviate_object=model.to_dict())
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Class may not have been created properly.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Create class", response)

        return CollectionObject(self._connection, model.name, model.properties)

    def get(self, collection_name: str, model: Type[BaseProperty]) -> CollectionObject:
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
        return CollectionObject(self._connection, collection_name, model)

    def get_dynamic(self, collection_name: str) -> Tuple[CollectionObject, Type[BaseProperty]]:
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

        return CollectionObject(self._connection, collection_name, model), model
