from typing import Optional, Type
from weaviate.collections.classes.internal import Properties, References
from weaviate.collections.collections.base import _CollectionsBase
from weaviate.collections.collection.sync import Collection
from weaviate.collections.classes.config import CollectionConfig
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _Collections(_CollectionsBase[ConnectionSync]):
    @executor.no_wrapping
    def use(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> Collection[Properties, References]:
        collection = self._use(
            name=name,
            data_model_properties=data_model_properties,
            data_model_references=data_model_references,
            skip_argument_validation=skip_argument_validation,
        )
        assert isinstance(collection, Collection)
        return collection

    @executor.no_wrapping
    def create_from_dict(self, config: dict) -> Collection:
        collection = executor.result(self._create_from_dict(config))
        assert isinstance(collection, Collection)
        return collection

    @executor.no_wrapping
    def create_from_config(self, config: CollectionConfig) -> Collection:
        collection = executor.result(self._create_from_config(config))
        assert isinstance(collection, Collection)
        return collection
