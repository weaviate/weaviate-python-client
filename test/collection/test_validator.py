from dataclasses import dataclass
from typing import Callable, Dict, List
from unittest.mock import Mock

import pytest


from weaviate.collections.classes.config import Configure
from weaviate.collections.collections import _Collections
from weaviate.collections.config import _ConfigCollection
from weaviate.collections.data import _DataCollection
from weaviate.collections.tenants import _Tenants
from weaviate.connect import Connection


@dataclass
class TestableFunction:
    __test__ = False
    func: Callable
    err: str


@pytest.fixture
def mock_connection():
    mock = Mock(spec=Connection)
    mock.server_version = "1.0.0"
    return mock


@pytest.fixture
def collections(mock_connection: Connection):
    return _Collections(mock_connection)


@pytest.fixture
def config(mock_connection: Connection):
    return _ConfigCollection(mock_connection, "Dummy", None)


@pytest.fixture
def data(mock_connection: Connection):
    return _DataCollection(mock_connection, "Dummy", None, None)


@pytest.fixture
def tenants(mock_connection: Connection):
    return _Tenants(mock_connection, "Dummy")


@pytest.fixture
def functions(
    collections: _Collections, config: _ConfigCollection, data: _DataCollection, tenants: _Tenants
) -> Dict[str, List[TestableFunction]]:
    return {
        "collections.get": [
            TestableFunction(
                lambda: collections.get(1),
                "Argument 'name' must be typing.List[str], but got <class 'int'>",
            )
        ],
        "collections.delete": [
            TestableFunction(
                lambda: collections.delete(1),
                "Argument 'name' must be typing.Union[str, typing.List[str]], but got <class 'int'>",
            )
        ],
        "collections.exists": [
            TestableFunction(
                lambda: collections.exists(1),
                "Argument 'name' must be typing.Union[str, typing.List[str]], but got <class 'int'>",
            )
        ],
        "collections.list_all": [
            TestableFunction(
                lambda: collections.list_all(1),
                "Argument 'simple' must be <class 'bool'>, but got <class 'int'>",
            )
        ],
        "config.add_property": [
            TestableFunction(
                lambda: config.add_property(1),
                "Argument 'additional_property' must be one of typing.Union[weaviate.collections.classes.config.Property, weaviate.collections.classes.config.ReferenceProperty, weaviate.collections.classes.config.ReferencePropertyMultiTarget], but got <class 'int'>",
            )
        ],
        "config.get": [
            TestableFunction(
                lambda: config.get(1),
                "Argument 'simple' must be <class 'bool'>, but got <class 'int'>",
            )
        ],
        "config.update": [
            TestableFunction(
                lambda: config.update(description=1),
                "Argument 'description' must be one of typing.Union[str, NoneType], but got <class 'int'>",
            ),
            TestableFunction(
                lambda: config.update(inverted_index_config=1),
                "Argument 'inverted_index_config' must be one of typing.Union[weaviate.collections.classes.config._InvertedIndexConfigUpdate, NoneType], but got <class 'int'>",
            ),
            TestableFunction(
                lambda: config.update(inverted_index_config=Configure.inverted_index()),
                "Argument 'inverted_index_config' must be one of typing.Union[weaviate.collections.classes.config._InvertedIndexConfigUpdate, NoneType], but got <class 'weaviate.collections.classes.config._InvertedIndexConfigCreate'>",
            ),
            TestableFunction(
                lambda: config.update(replication_config=1),
                "Argument 'replication_config' must be one of typing.Union[weaviate.collections.classes.config._ReplicationConfigUpdate, NoneType], but got <class 'int'>",
            ),
            TestableFunction(
                lambda: config.update(replication_config=Configure.replication()),
                "Argument 'replication_config' must be one of typing.Union[weaviate.collections.classes.config._ReplicationConfigUpdate, NoneType], but got <class 'weaviate.collections.classes.config._ReplicationConfigCreate'>",
            ),
            TestableFunction(
                lambda: config.update(vector_index_config=1),
                "Argument 'vector_index_config' must be one of typing.Union[weaviate.collections.classes.config._VectorIndexConfigHNSWUpdate, weaviate.collections.classes.config._VectorIndexConfigFlatUpdate, NoneType], but got <class 'int'>",
            ),
            TestableFunction(
                lambda: config.update(vector_index_config=Configure.VectorIndex.hnsw()),
                "Argument 'vector_index_config' must be one of typing.Union[weaviate.collections.classes.config._VectorIndexConfigHNSWUpdate, weaviate.collections.classes.config._VectorIndexConfigFlatUpdate, NoneType], but got <class 'weaviate.collections.classes.config._VectorIndexConfigHNSWCreate'>",
            ),
        ],
        "data.delete_by_id": [
            TestableFunction(
                lambda: data.delete_by_id(1),
                "Argument 'uuid' must be one of typing.Union[str, uuid.UUID], but got <class 'int'>",
            ),
            TestableFunction(
                lambda: data.delete_by_id("1", "extra"), "too many positional arguments"
            ),
            TestableFunction(
                lambda: data.delete_by_id("1", extra="extra"),
                "got an unexpected keyword argument 'extra'",
            ),
        ],
        "data.delete_many": [
            TestableFunction(
                lambda: data.delete_many(1),
                "Argument 'where' must be <class 'weaviate.collections.classes.filters._Filters'>, but got <class 'int'>",
            ),
        ],
        "tenants.create": [
            TestableFunction(
                lambda: tenants.create(1),
                "Argument 'tenants' must be typing.List[weaviate.collections.classes.tenants.Tenant], but got <class 'int'>",
            ),
            TestableFunction(
                lambda: tenants.create(["who"]),
                "List element of argument 'tenants' must be <class 'weaviate.collections.classes.tenants.Tenant'>, but got <class 'str'>",
            ),
        ],
        "tenants.remove": [
            TestableFunction(
                lambda: tenants.remove(1),
                "Argument 'tenants' must be typing.List[str], but got <class 'int'>",
            ),
            TestableFunction(
                lambda: tenants.remove([1.1]),
                "List element of argument 'tenants' must be <class 'str'>, but got <class 'float'>",
            ),
        ],
        "tenants.update": [
            TestableFunction(
                lambda: tenants.update(1),
                "Argument 'tenants' must be typing.List[weaviate.collections.classes.tenants.Tenant], but got <class 'int'>",
            ),
            TestableFunction(
                lambda: tenants.update(["who"]),
                "List element of argument 'tenants' must be <class 'weaviate.collections.classes.tenants.Tenant'>, but got <class 'str'>",
            ),
        ],
    }


@pytest.fixture
def test(
    request: pytest.FixtureRequest, functions: Dict[str, TestableFunction]
) -> TestableFunction:
    return functions[request.param[0]][request.param[1]]


@pytest.mark.parametrize(
    "test",
    [
        ("config.add_property", 0),
        ("config.get", 0),
        ("config.update", 0),
        ("config.update", 1),
        ("config.update", 2),
        ("config.update", 3),
        ("config.update", 4),
        ("config.update", 5),
        ("data.delete_by_id", 0),
        ("data.delete_by_id", 1),
        ("data.delete_by_id", 2),
        ("data.delete_many", 0),
        ("tenants.create", 0),
        ("tenants.create", 1),
        ("tenants.remove", 0),
        ("tenants.remove", 1),
        ("tenants.update", 0),
        ("tenants.update", 1),
    ],
    indirect=True,
    ids=lambda x: x[0] + str(x[1]),
)
def test_validator(test: TestableFunction):
    with pytest.raises(TypeError) as e:
        test.func()
    assert e.value.args[0] == test.err
