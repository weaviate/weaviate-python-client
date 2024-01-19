from weaviate.collections.classes.aggregate import Metrics
from .tenants import Tenant

from .config import (
    Configure,
    Reconfigure,
    DataType,
    Multi2VecField,
    Property,
    ReferenceProperty,
    ReferencePropertyMultiTarget,
    StopwordsPreset,
    Tokenization,
    VectorDistance,
)
from .data import (
    DataObject,
    DataReference,
    GeoCoordinate,
    Reference,
)
from .generics import Nested, CrossReference, ReferenceAnnotation, CrossReferenceAnnotation
from .query import (
    Filter,
    FromNested,
    FromReference,
    FromReferenceMultiTarget,
    HybridFusion,
    MetadataQuery,
    Move,
    QueryNested,
    QueryReference,
)

# make sure to import all classes that should be available in the weaviate module
from . import batch, config, data, generics, init, query, tenants  # noqa: F401

__all__ = [
    "Configure",
    "Reconfigure",
    "CrossReference",
    "CrossReferenceAnnotation",
    "DataObject",
    "DataReference",
    "DataType",
    "Filter",
    "HybridFusion",
    "FromNested",
    "FromReference",
    "FromReferenceMultiTarget",
    "GeoCoordinate",
    "MetadataQuery",
    "Metrics",
    "Move",
    "Multi2VecField",
    "Nested",
    "Property",
    "QueryNested",
    "QueryReference",
    "Reference",
    "ReferenceAnnotation",
    "ReferenceProperty",
    "ReferencePropertyMultiTarget",
    "StopwordsPreset",
    "Tenant",
    "Tokenization",
    "VectorDistance",
]
