from enum import Enum


class VectorIndexType(str, Enum):
    """The available vector index types in Weaviate.

    Attributes:
        HNSW: Hierarchical Navigable Small World (HNSW) index.
        FLAT: Flat index.
    """

    HNSW = "hnsw"
    FLAT = "flat"
