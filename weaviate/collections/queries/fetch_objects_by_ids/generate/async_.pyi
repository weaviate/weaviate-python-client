from typing import Generic, Iterable, List, Literal, Optional, Type, Union, overload

from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, Sorting
from weaviate.collections.classes.internal import (
    CrossReferences,
    GenerativeReturn,
    GenerativeReturnType,
    ReturnProperties,
    ReturnReferences,
    _GenerativeConfigRuntime,
    _GroupedTask,
    _SinglePrompt,
)
from weaviate.collections.classes.types import Properties, References, TProperties, TReferences
from weaviate.connect.v4 import ConnectionAsync
from weaviate.types import INCLUDE_VECTOR, UUID

from .executor import _FetchObjectsByIDsGenerateExecutor

class _FetchObjectsByIDsGenerateAsync(
    Generic[Properties, References],
    _FetchObjectsByIDsGenerateExecutor[ConnectionAsync, Properties, References],
):
    @overload
    async def fetch_objects_by_ids(
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
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None,
    ) -> GenerativeReturn[Properties, References]: ...
    @overload
    async def fetch_objects_by_ids(
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
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES,
    ) -> GenerativeReturn[Properties, CrossReferences]: ...
    @overload
    async def fetch_objects_by_ids(
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
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Type[TReferences],
    ) -> GenerativeReturn[Properties, TReferences]: ...
    @overload
    async def fetch_objects_by_ids(
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
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> GenerativeReturn[TProperties, References]: ...
    @overload
    async def fetch_objects_by_ids(
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
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> GenerativeReturn[TProperties, CrossReferences]: ...
    @overload
    async def fetch_objects_by_ids(
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
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> GenerativeReturn[TProperties, TReferences]: ...
    @overload
    async def fetch_objects_by_ids(
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
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> GenerativeReturnType[Properties, References, TProperties, TReferences]: ...
