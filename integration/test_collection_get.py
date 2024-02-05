from dataclasses import dataclass
from typing import Any, TypedDict, Dict

import pytest
from _pytest.fixtures import SubRequest
from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from integration.conftest import CollectionFactoryGet, CollectionFactory
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

        col = collection_factory_get(request.node.name, Right, Right)
    else:
        col = collection_factory_get(request.node.name, Dict[str, str], Dict[str, str])
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


WRONG_PROPERTIES_ERROR_MSG = "properties can only be a dict type, e.g. Dict[str, Any], or a class that inherits from TypedDict"
WRONG_REFERENCES_ERROR_MSG = "references can only be a dict type, e.g. Dict[str, Any], or a class that inherits from TypedDict"


class WrongEmpty:
    name: str


@dataclass
class WrongDC:
    name: str


class WrongInit:
    name: str


class WrongPyd(BaseModel):
    name: str


@pydantic_dataclass
class WrongPydDC:
    name: str


@pytest.mark.parametrize("properties", [None, WrongEmpty, WrongDC, WrongInit, WrongPyd, WrongPydDC])
@pytest.mark.parametrize("references", [None, WrongEmpty, WrongDC, WrongInit, WrongPyd, WrongPydDC])
def test_get_with_wrong_generics(
    collection_factory_get: CollectionFactoryGet, properties: Any, references: Any
) -> None:
    if properties is None and references is None:
        pytest.skip("Not an error to not have properties and not have references")

    with pytest.raises(InvalidDataModelException) as error:
        collection_factory_get("NotImportant", properties, references)

    if properties is not None:
        assert error.value.args[0] == WRONG_PROPERTIES_ERROR_MSG
    else:
        assert error.value.args[0] == WRONG_REFERENCES_ERROR_MSG


def test_get_with_skip_validation(
    collection_factory_get: CollectionFactoryGet, collection_factory: CollectionFactory
) -> None:
    collection_dummy = collection_factory()

    collection = collection_factory_get(collection_dummy.name, skip_argument_validation=True)
    with pytest.raises(AttributeError):
        collection.data.insert(properties=[])
    with pytest.raises(TypeError):
        collection.query.bm25(query=5)  # type: ignore
    with pytest.raises(TypeError):
        collection.query.near_vector(vector="test")  # type: ignore
