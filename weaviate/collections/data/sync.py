from typing import Generic, Type
from weaviate.connect import executor
from weaviate.collections.classes.internal import Properties, TProperties
from weaviate.collections.classes.types import _check_properties_generic
from weaviate.collections.data.executor import _DataCollectionExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _DataCollection(Generic[Properties], _DataCollectionExecutor[ConnectionSync]):
    def with_data_model(self, data_model: Type[TProperties]) -> "_DataCollection[TProperties]":
        _check_properties_generic(data_model)
        return _DataCollection[TProperties](
            self._connection,
            self.name,
            self._consistency_level,
            self._tenant,
            self._validate_arguments,
            data_model,
        )
