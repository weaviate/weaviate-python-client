from typing import (
    Optional,
    Type,
)

from weaviate.collections.classes.config import (
    CollectionConfig,
)
from weaviate.collections.classes.internal import References
from weaviate.collections.classes.types import (
    Properties,
)
from weaviate.collections.collection import CollectionAsync
from weaviate.collections.collections.base import _CollectionsBase
from weaviate.connect import impl
from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionAsync


@impl.generate("async")
class _CollectionsAsync(_CollectionsBase[ConnectionAsync]):
    def get(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> CollectionAsync[Properties, References]:
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
    ) -> CollectionAsync[Properties, References]:
        collection = self._executor.use(
            connection=self._connection,
            name=name,
            data_model_properties=data_model_properties,
            data_model_references=data_model_references,
            skip_argument_validation=skip_argument_validation,
        )
        assert isinstance(collection, CollectionAsync)
        return collection

    async def create_from_dict(self, config: dict) -> CollectionAsync:
        collection = await aresult(
            self._executor.create_from_dict(config, connection=self._connection)
        )
        assert isinstance(collection, CollectionAsync)
        return collection

    async def create_from_config(self, config: CollectionConfig) -> CollectionAsync:
        collection = await aresult(
            self._executor.create_from_config(config, connection=self._connection)
        )
        assert isinstance(collection, CollectionAsync)
        return collection
