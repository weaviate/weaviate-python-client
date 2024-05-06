from weaviate.collections.aggregations.hybrid import _Hybrid
from weaviate.collections.aggregations.near_image import _NearImage
from weaviate.collections.aggregations.near_object import _NearObject
from weaviate.collections.aggregations.near_text import _NearText
from weaviate.collections.aggregations.near_vector import _NearVector
from weaviate.collections.aggregations.over_all import _OverAll


class _AggregateCollection(_Hybrid, _NearImage, _NearObject, _NearText, _NearVector, _OverAll):
    pass
