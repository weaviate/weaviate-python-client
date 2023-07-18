import hashlib
import typing
import uuid as uuid_package
from dataclasses import dataclass
from typing import Type, Optional, Any, List, Dict, Generic, TypeAlias, TypeVar, Tuple

from pydantic import BaseModel, Field, create_model, field_validator
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collection.collection_base import CollectionBase, CollectionObjectBase
from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.weaviate_types import (
    CollectionConfigBase,
    PYTHON_TYPE_TO_DATATYPE,
    UUID,
    Metadata,
    MetadataReturn,
)


class BaseProperty(BaseModel):
    uuid: UUID = Field(default=uuid_package.uuid4())
    vector: Optional[List[float]] = None

    def props_to_dict(self) -> Dict[str, Any]:
        return {
            name: value
            for name, value in self.model_fields.items()
            if name not in BaseProperty.model_fields
        }

    @field_validator("uuid")
    def create_valid_uuid(cls, input_uuid: UUID) -> uuid_package.UUID:
        if isinstance(input_uuid, uuid_package.UUID):
            return input_uuid

        # see if str is already a valid uuid
        try:
            return uuid_package.UUID(input_uuid)
        except ValueError:
            hex_string = hashlib.md5(input_uuid.encode("UTF-8")).hexdigest()
            return uuid_package.UUID(hex=hex_string)

    @staticmethod
    def type_to_dict(model: Type["BaseProperty"]) -> List[Dict[str, Any]]:
        types = typing.get_type_hints(model)
        return [
            {
                "name": name.capitalize(),
                "dataType": [
                    PYTHON_TYPE_TO_DATATYPE[BaseProperty._remove_optional_type(types[name])]
                ],
            }
            for name in model.model_fields.keys()
            if name not in BaseProperty.model_fields
        ]

    @staticmethod
    def _remove_optional_type(python_type: Type[type]) -> Type[type]:
        args = typing.get_args(python_type)
        if len(args) == 0:
            return python_type

        return [t for t in args if t is not None][0]


UserModelType: TypeAlias = Type[BaseProperty]

Model = TypeVar("Model", bound=BaseProperty)


class CollectionConfigModel(CollectionConfigBase, Generic[Model]):
    properties: Type[Model]

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["properties"] = self.properties.type_to_dict(self.properties)

        return ret_dict


@dataclass
class _Object(Generic[Model]):
    data: Model
    metadata: MetadataReturn


class CollectionObjectModel(CollectionObjectBase, Generic[Model]):
    def __init__(self, connection: Connection, name: str, dynamic_model: Type[Model]) -> None:
        super().__init__(connection, name)
        self._model: Type[Model] = dynamic_model

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

    def get_by_id(
        self, uuid: UUID, metadata: Optional[Metadata] = None
    ) -> Optional[_Object[Model]]:
        ret = self._get_by_id(uuid=uuid, metadata=metadata)
        if ret is None:
            return None
        return self._json_to_object(ret)

    def get(self, metadata: Optional[Metadata] = None) -> Optional[List[_Object[Model]]]:
        ret = self._get(metadata=metadata)
        if ret is None:
            return None

        return [self._json_to_object(obj) for obj in ret["objects"]]

    def _json_to_object(self, obj: Dict[str, Any]) -> _Object[Model]:
        return _Object[Model](data=self._model(**obj["properties"]), metadata=MetadataReturn(**obj))


class CollectionModel(CollectionBase, Generic[Model]):
    def __init__(self, connection: Connection, model: Type[Model]):
        super().__init__(connection)
        self._model = model

    def create(self, config: CollectionConfigModel) -> CollectionObjectModel[Model]:
        super()._create(config)

        return CollectionObjectModel[Model](self._connection, config.name, self._model)

    def get(self, collection_name: str) -> CollectionObjectModel[Model]:
        path = f"/schema/{collection_name.capitalize()}"

        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Schema could not be retrieved.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Get schema", response)

        response_json = response.json()
        model_props = self._model.type_to_dict(self._model)
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
        return CollectionObjectModel[Model](self._connection, collection_name, self._model)

    def get_dynamic(
        self, collection_name: str
    ) -> Tuple[CollectionObjectModel[Model], UserModelType]:
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
        model = create_model(response_json["class"], **fields, __base__=self._model)

        return CollectionObjectModel(self._connection, collection_name, model), model
