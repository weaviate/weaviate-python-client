from typing import Optional, Type
from weaviate.collections.classes.internal import Properties, References
from weaviate.collections.collections.base import _CollectionsBase
from weaviate.collections.collection.sync import Collection
from weaviate.collections.classes.config import CollectionConfig
from weaviate.connect import impl
from weaviate.connect.executor import result
from weaviate.connect.v4 import ConnectionSync


@impl.generate("sync")
class _Collections(_CollectionsBase[ConnectionSync]):
    def get(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> Collection[Properties, References]:
        return self.use(
            name=name,
            data_model_properties=data_model_properties,
            data_model_references=data_model_references,
            skip_argument_validation=skip_argument_validation,
        )

    def use(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> Collection[Properties, References]:
        collection = self._executor.use(
            connection=self._connection,
            name=name,
            data_model_properties=data_model_properties,
            data_model_references=data_model_references,
            skip_argument_validation=skip_argument_validation,
        )
        assert isinstance(collection, Collection)
        return collection

    def create_from_dict(self, config: dict) -> Collection:
        collection = result(self._executor.create_from_dict(config, connection=self._connection))
        assert isinstance(collection, Collection)
        return collection

    def create_from_config(self, config: CollectionConfig) -> Collection:
        collection = result(self._executor.create_from_config(config, connection=self._connection))
        assert isinstance(collection, Collection)
        return collection
