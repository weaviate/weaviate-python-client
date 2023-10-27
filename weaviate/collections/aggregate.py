from weaviate.collections.aggregations.over_all import _OverAll, _OverAllGroupBy
from weaviate.collections.aggregations.near_image import _NearImage, _NearImageGroupBy
from weaviate.collections.aggregations.near_object import _NearObject, _NearObjectGroupBy
from weaviate.collections.aggregations.near_text import _NearText, _NearTextGroupBy
from weaviate.collections.aggregations.near_vector import _NearVector, _NearVectorGroupBy


class _AggregateCollection(_OverAll, _NearImage, _NearObject, _NearText, _NearVector):
    pass


class _AggregateGroupByCollection(
    _OverAllGroupBy, _NearImageGroupBy, _NearObjectGroupBy, _NearTextGroupBy, _NearVectorGroupBy
):
    pass
