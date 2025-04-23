from typing import Generic, Type
from weaviate.connect import executor
from weaviate.collections.classes.internal import Properties, TProperties
from weaviate.collections.data.executor import _DataCollectionExecutor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.collections.classes.types import _check_properties_generic


@executor.wrap("async")
class _DataCollectionAsync(Generic[Properties], _DataCollectionExecutor[ConnectionAsync]):
    def with_data_model(self, data_model: Type[TProperties]) -> "_DataCollectionAsync[TProperties]":
        _check_properties_generic(data_model)
        return _DataCollectionAsync[TProperties](
            self._connection,
            self.name,
            self._consistency_level,
            self._tenant,
            self._validate_arguments,
            data_model,
        )
