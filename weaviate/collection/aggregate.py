from weaviate.collection.aggregations.over_all import _OverAll, _OverAllGroupBy
from weaviate.collection.aggregations.near_image import _NearImage, _NearImageGroupBy
from weaviate.collection.aggregations.near_object import _NearObject, _NearObjectGroupBy
from weaviate.collection.aggregations.near_text import _NearText, _NearTextGroupBy
from weaviate.collection.aggregations.near_vector import _NearVector, _NearVectorGroupBy


class _AggregateCollection(_OverAll, _NearImage, _NearObject, _NearText, _NearVector):
    pass


class _AggregateGroupByCollection(
    _OverAllGroupBy, _NearImageGroupBy, _NearObjectGroupBy, _NearTextGroupBy, _NearVectorGroupBy
):
    pass
