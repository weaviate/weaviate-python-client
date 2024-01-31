import pytest
from weaviate.config import ConnectionConfig
from weaviate.connect import ConnectionV4, ConnectionParams


@pytest.fixture
def connection() -> ConnectionV4:
    con = ConnectionV4(
        ConnectionParams.from_url("http://localhost:8080", 50051),
        None,
        (10, 60),
        None,
        True,
        None,
        ConnectionConfig(),
        None,
    )
    con._Connection__connected = True
    return con
