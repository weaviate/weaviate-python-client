from abc import abstractmethod
from typing import Generic, Iterable, List, Optional, Union

from weaviate.collections.classes.generative import (
    _GenerativeConfigRuntime,
    _GroupedTask,
    _SinglePrompt,
)
from weaviate.collections.classes.grpc import METADATA, Sorting
from weaviate.collections.classes.internal import (
    GenerativeReturnType,
    QueryReturnType,
    ReturnProperties,
    ReturnReferences,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base import _BaseGenerate, _BaseQuery
from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType
from weaviate.types import UUID, INCLUDE_VECTOR


class _FetchObjectsByIDsGenerateBase(
    Generic[ConnectionType, Properties, References],
    _BaseGenerate[ConnectionType, Properties, References],
):
    @abstractmethod
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None
    ) -> ExecutorResult[GenerativeReturnType[Properties, References, TProperties, TReferences]]:
        """Perform retrieval-augmented generation (RAG) on the results of a simple get query of objects matching the provided IDs in this collection.

        See the docstring of `fetch_objects` for more information on the arguments.
        """
        raise NotImplementedError()


class _FetchObjectsByIDsQueryBase(
    Generic[ConnectionType, Properties, References],
    _BaseQuery[ConnectionType, Properties, References],
):
    @abstractmethod
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None
    ) -> ExecutorResult[QueryReturnType[Properties, References, TProperties, TReferences]]:
        """Perform a special case of fetch_objects based on filters on uuid.

        See the docstring of `fetch_objects` for more information on the arguments.
        """
        raise NotImplementedError()
