from dataclasses import dataclass
from typing import TypedDict, Dict

import pytest
from _pytest.fixtures import SubRequest
from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from integration.conftest import CollectionFactoryGet
from weaviate.collections import Collection
from weaviate.collections.data import _Data
from weaviate.exceptions import InvalidDataModelException


@pytest.mark.parametrize("use_typed_dict", [True, False])
def test_get_with_dict_generic(
    collection_factory_get: CollectionFactoryGet, request: SubRequest, use_typed_dict: bool
) -> None:
    if use_typed_dict:

        class Right(TypedDict):
            name: str

        col = collection_factory_get(request.node.name, Right)
    else:
        col = collection_factory_get(request.node.name, Dict[str, str])
    assert isinstance(col, Collection)


def test_data_with_data_model_with_dict_generic(
    collection_factory_get: CollectionFactoryGet, request: SubRequest
) -> None:
    class Right(TypedDict):
        name: str

    col = collection_factory_get(request.node.name)
    assert isinstance(col, Collection)
    data = col.data.with_data_model(Right)
    assert isinstance(data, _Data)


WRONG_GENERIC_ERROR_MSG = "properties can only be a dict type, e.g. Dict[str, Any], or a class that inherits from TypedDict"


def test_get_with_empty_class_generic(
    collection_factory_get: CollectionFactoryGet, request: SubRequest
) -> None:
    class Wrong:
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        collection_factory_get("NotImportant", Wrong)  # type: ignore # runtime testing incorrect usage
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_dataclass_generic(
    collection_factory_get: CollectionFactoryGet, request: SubRequest
) -> None:
    @dataclass
    class Wrong:
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        collection_factory_get("NotImportant", Wrong)  # type: ignore # runtime testing incorrect usage
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_initialisable_class_generic(
    collection_factory_get: CollectionFactoryGet, request: SubRequest
) -> None:
    class Wrong:
        name: str

        def __init__(self, name: str) -> None:
            self.name = name

    with pytest.raises(InvalidDataModelException) as error:
        collection_factory_get("NotImportant", Wrong)  # type: ignore # runtime testing incorrect usage
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_pydantic_class_generic(
    collection_factory_get: CollectionFactoryGet, request: SubRequest
) -> None:
    class Wrong(BaseModel):
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        collection_factory_get("NotImportant", Wrong)  # type: ignore # runtime testing incorrect usage
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_pydantic_dataclass_generic(
    collection_factory_get: CollectionFactoryGet, request: SubRequest
) -> None:
    @pydantic_dataclass
    class Wrong:
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        collection_factory_get("NotImportant", Wrong)  # type: ignore # runtime testing incorrect usage
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG
