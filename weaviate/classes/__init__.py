from .config import ConsistencyLevel

# make sure to import all classes that should be available in the weaviate module
from . import aggregate, batch, config, data, generics, init, query, tenants  # noqa: F401

__all__ = [
    "aggregate",
    "batch",
    "config",
    "ConsistencyLevel",
    "data",
    "generics",
    "init",
    "query",
    "tenants",
]
