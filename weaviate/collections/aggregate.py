from weaviate.collections.aggregations.over_all import _OverAllAsync, _OverAll
from weaviate.collections.aggregations.near_image import _NearImageAsync, _NearImage
from weaviate.collections.aggregations.near_object import _NearObjectAsync, _NearObject
from weaviate.collections.aggregations.near_text import _NearTextAsync, _NearText
from weaviate.collections.aggregations.near_vector import _NearVectorAsync, _NearVector


class _AggregateCollectionAsync(
    _OverAllAsync, _NearImageAsync, _NearObjectAsync, _NearTextAsync, _NearVectorAsync
):
    pass


class _AggregateCollection(_OverAll, _NearImage, _NearObject, _NearText, _NearVector):
    pass
