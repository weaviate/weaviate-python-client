from weaviate.collections.aggregations.hybrid import _HybridAsync, _Hybrid
from weaviate.collections.aggregations.near_image import _NearImageAsync, _NearImage
from weaviate.collections.aggregations.near_object import _NearObjectAsync, _NearObject
from weaviate.collections.aggregations.near_text import _NearTextAsync, _NearText
from weaviate.collections.aggregations.near_vector import _NearVectorAsync, _NearVector
from weaviate.collections.aggregations.over_all import _OverAllAsync, _OverAll


class _AggregateCollectionAsync(
    _HybridAsync, _NearImageAsync, _NearObjectAsync, _NearTextAsync, _NearVectorAsync, _OverAllAsync
):
    pass


class _AggregateCollection(_Hybrid, _NearImage, _NearObject, _NearText, _NearVector, _OverAll):
    pass
