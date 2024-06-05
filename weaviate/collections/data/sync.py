from typing import Generic, Type
from weaviate import syncify
from weaviate.collections.classes.internal import Properties
from weaviate.collections.classes.types import TProperties, _check_properties_generic
from weaviate.collections.data.data import _DataCollectionAsync


@syncify.convert
class _DataCollection(Generic[Properties], _DataCollectionAsync[Properties]):
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
