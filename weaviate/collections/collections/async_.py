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


@impl.wrap("async")
class _CollectionsAsync(_CollectionsBase[ConnectionAsync]):
    @impl.no_wrapping
    def use(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> CollectionAsync[Properties, References]:
        collection = self._use(
            name=name,
            data_model_properties=data_model_properties,
            data_model_references=data_model_references,
            skip_argument_validation=skip_argument_validation,
        )
        assert isinstance(collection, CollectionAsync)
        return collection

    @impl.no_wrapping
    async def create_from_dict(self, config: dict) -> CollectionAsync:
        collection = await aresult(self._create_from_dict(config))
        assert isinstance(collection, CollectionAsync)
        return collection

    @impl.no_wrapping
    async def create_from_config(self, config: CollectionConfig) -> CollectionAsync:
        collection = await aresult(self._create_from_config(config))
        assert isinstance(collection, CollectionAsync)
        return collection
