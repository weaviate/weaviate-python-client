from weaviate.collections.aggregations.hybrid import _Hybrid, _HybridAsync
from weaviate.collections.aggregations.near_image import _NearImage, _NearImageAsync
from weaviate.collections.aggregations.near_object import _NearObject, _NearObjectAsync
from weaviate.collections.aggregations.near_text import _NearText, _NearTextAsync
from weaviate.collections.aggregations.near_vector import _NearVector, _NearVectorAsync
from weaviate.collections.aggregations.over_all import _OverAll, _OverAllAsync


class _AggregateCollectionAsync(
    _HybridAsync,
    _NearImageAsync,
    _NearObjectAsync,
    _NearTextAsync,
    _NearVectorAsync,
    _OverAllAsync,
):
    pass


class _AggregateCollection(_Hybrid, _NearImage, _NearObject, _NearText, _NearVector, _OverAll):
    pass
