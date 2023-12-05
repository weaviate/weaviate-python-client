import datetime
from typing import Any, Dict, Generic, Optional, Type, Union, cast, get_type_hints

from requests.exceptions import ConnectionError as RequestsConnectionError
from weaviate.collections.classes.types import Properties
from weaviate.collections.config import _ConfigCollection

from weaviate.connect import Connection
from weaviate.collections.classes.config import (
    _CollectionConfigCreateBase,
    _CollectionConfig,
    _CollectionConfigSimple,
    _ReferenceDataType,
    _ReferenceDataTypeMultiTarget,
    DataType,
)
from weaviate.collections.classes.config_methods import (
    _collection_configs_from_json,
    _collection_configs_simple_from_json,
)
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.util import _capitalize_first_letter
import uuid as uuid_package


class _TypeHints(Generic[Properties]):
    def __init__(
        self,
        config: _ConfigCollection,
        type_hints: Optional[Union[Type[Properties], Dict[str, DataType]]],
    ) -> None:
        self._config = config
        self._type_hints: Optional[Type[Properties]] = None
        self._cached_datatypes: Optional[
            Dict[str, Union[DataType, _ReferenceDataType, _ReferenceDataTypeMultiTarget]]
        ] = None
        if type_hints is None:
            self.__refresh_cashed_datatypes()
        elif isinstance(type_hints, type):
            self._type_hints = type_hints
        else:
            self._cached_datatypes = cast(
                Dict[str, Union[DataType, _ReferenceDataType, _ReferenceDataTypeMultiTarget]],
                type_hints,
            )

    def __refresh_cashed_datatypes(self) -> None:
        config = self._config.get()
        self._cached_datatypes = {prop.name: prop.data_type for prop in config.properties}

    def deserialize_properties(self, data: Dict[str, Any]) -> Properties:
        if self._type_hints is None:
            return cast(
                Properties,
                {
                    key: self._deserialize_primitive_from_cache(val, name=key)
                    for key, val in data.items()
                },
            )
        else:
            hints = get_type_hints(self._type_hints)
            return cast(
                Properties,
                {
                    key: self._deserialize_primitive_from_user_hints(val, type_value=hints)
                    for key, val in data.items()
                },
            )

    def _deserialize_primitive_from_user_hints(self, value: Any, type_value: Optional[Any]) -> Any:
        if type_value is None:
            return value
        if type_value == uuid_package.UUID:
            return uuid_package.UUID(value)
        if type_value == datetime.datetime:
            return datetime.datetime.fromisoformat(value)
        if isinstance(type_value, list):
            return [
                self._deserialize_primitive_from_user_hints(val, type_value[idx])
                for idx, val in enumerate(value)
            ]
        return value

    def _deserialize_primitive_from_cache(self, value: Any, name: str) -> Any:
        assert self._cached_datatypes is not None
        if name not in self._cached_datatypes:
            self.__refresh_cashed_datatypes()
        dt = self._cached_datatypes.get(name, None)  # refs are not in here
        if dt == DataType.UUID:
            return uuid_package.UUID(value)
        if dt == DataType.UUID_ARRAY:
            return [uuid_package.UUID(val) for val in value]
        if dt == DataType.DATE:
            return datetime.datetime.fromisoformat(value)
        if dt == DataType.DATE_ARRAY:
            return [datetime.datetime.fromisoformat(val) for val in value]
        return value


class _CollectionBase:
    def __init__(self, name: str) -> None:
        self.name = _capitalize_first_letter(name)


class _CollectionsBase:
    def __init__(self, connection: Connection):
        self._connection = connection

    def _create(
        self,
        config: _CollectionConfigCreateBase,
    ) -> str:
        weaviate_object = config._to_dict()

        try:
            response = self._connection.post(path="/schema", weaviate_object=weaviate_object)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Class may not have been created properly.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Create class", response)

        collection_name = response.json()["class"]
        assert isinstance(collection_name, str)
        return collection_name

    def _exists(self, name: str) -> bool:
        path = f"/schema/{name}"
        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Existenz of class.") from conn_err

        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        raise UnexpectedStatusCodeException("collection exists", response)

    def _delete(self, name: str) -> None:
        path = f"/schema/{name}"
        try:
            response = self._connection.delete(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Deletion of class.") from conn_err
        if response.status_code == 200:
            return

        UnexpectedStatusCodeException("Delete collection", response)

    def _get_all(self) -> Dict[str, _CollectionConfig]:
        try:
            response = self._connection.get(path="/schema")
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Get schema.") from conn_err
        if response.status_code == 200:
            res = response.json()
            return _collection_configs_from_json(res)
        raise UnexpectedStatusCodeException("Get schema", response)

    def _get_simple(self) -> Dict[str, _CollectionConfigSimple]:
        try:
            response = self._connection.get(path="/schema")
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Get schema.") from conn_err
        if response.status_code == 200:
            res = response.json()
            return _collection_configs_simple_from_json(res)
        raise UnexpectedStatusCodeException("Get schema", response)
