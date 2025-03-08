from weaviate import syncify
from weaviate.collections.vectorindex.convert import _ConvertCollectionAsync


@syncify.convert
class _ConvertCollection(_ConvertCollectionAsync):
    pass
