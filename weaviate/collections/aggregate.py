from weaviate.collections.aggregations.over_all import _OverAll
from weaviate.collections.aggregations.near_image import _NearImage
from weaviate.collections.aggregations.near_object import _NearObject
from weaviate.collections.aggregations.near_text import _NearText
from weaviate.collections.aggregations.near_vector import _NearVector


class _AggregateCollection(_OverAll, _NearImage, _NearObject, _NearText, _NearVector):
    pass
