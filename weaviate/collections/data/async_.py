from typing import Generic
from weaviate.connect import impl
from weaviate.collections.classes.internal import Properties
from weaviate.collections.data.base import _DataBase
from weaviate.connect.v4 import ConnectionAsync


@impl.generate("async")
class _DataCollectionAsync(Generic[Properties], _DataBase[ConnectionAsync]):
    # def with_data_model(self, data_model: Type[TProperties]) -> "_DataCollection[TProperties]":
    #     _check_properties_generic(data_model)
    #     return _DataCollection[TProperties](
    #         self._connection,
    #         self.name,
    #         self._consistency_level,
    #         self._tenant,
    #         self._validate_arguments,
    #         data_model,
    #     )
    pass
