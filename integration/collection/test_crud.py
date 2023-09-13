from dataclasses import dataclass
from typing import Dict, TypedDict

import pytest as pytest

from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from weaviate.collection import Collection
from weaviate.collection.classes.config import (
    Property,
    DataType,
    VectorizerFactory,
)
from weaviate.collection.collection import CollectionObject
from weaviate.exceptions import InvalidDataModelException


def test_create_get_and_delete(collection_basic: Collection):
    name = "TestCreateAndDeleteNoGeneric"
    col = collection_basic.create(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )
    assert collection_basic.exists(name)
    assert isinstance(col, CollectionObject)

    col = collection_basic.get(name)
    assert isinstance(col, CollectionObject)

    collection_basic.delete(name)
    assert not collection_basic.exists(name)


@pytest.mark.parametrize("use_typed_dict", [True, False])
def test_get_with_dict_generic(collection_basic: Collection, use_typed_dict: bool):
    name = "TestGetWithDictGeneric"
    if use_typed_dict:

        class Right(TypedDict):
            name: str

        col = collection_basic.get(name, Right)
    else:
        col = collection_basic.get(name, Dict[str, str])
    assert isinstance(col, CollectionObject)


WRONG_GENERIC_ERROR_MSG = "data_model can only be a dict type, e.g. Dict[str, str], or a class that inherits from TypedDict"


def test_get_with_empty_class_generic(collection_basic: Collection):
    class Wrong:
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        collection_basic.get("NotImportant", Wrong)
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_dataclass_generic(collection_basic: Collection):
    @dataclass
    class Wrong:
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        collection_basic.get("NotImportant", Wrong)
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_initialisable_class_generic(collection_basic: Collection):
    class Wrong:
        name: str

        def __init__(self, name: str):
            self.name = name

    with pytest.raises(InvalidDataModelException) as error:
        collection_basic.get("NotImportant", Wrong)
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_pydantic_class_generic(collection_basic: Collection):
    class Wrong(BaseModel):
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        collection_basic.get("NotImportant", Wrong)
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_pydantic_dataclass_generic(collection_basic: Collection):
    @pydantic_dataclass
    class Wrong:
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        collection_basic.get("NotImportant", Wrong)
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_collection_name_capitalization(collection_basic: Collection):
    name_small = "collectionCapitalizationTest"
    name_big = "CollectionCapitalizationTest"
    collection = collection_basic.create(
        name=name_small,
        vectorizer_config=VectorizerFactory.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
    )

    assert collection.name == name_big
    collection_basic.delete(name_small)
    assert not collection_basic.exists(name_small)
    assert not collection_basic.exists(name_big)
