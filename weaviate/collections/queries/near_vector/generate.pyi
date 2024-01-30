from typing import Generic, List, Literal, Optional, Type, Union, overload
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, GroupBy, Rerank
from weaviate.collections.classes.internal import (
    GenerativeReturn,
    GenerativeGroupByReturn,
    CrossReferences,
)
from weaviate.collections.classes.types import (
    Properties,
    TProperties,
    References,
    TReferences,
    Vectors,
)
from weaviate.collections.queries.base import _BaseQuery

class _NearVectorGenerate(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> GenerativeReturn[Properties, None, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> GenerativeGroupByReturn[Properties, None, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> GenerativeReturn[Properties, CrossReferences, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> GenerativeGroupByReturn[Properties, CrossReferences, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> GenerativeReturn[Properties, TReferences, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> GenerativeGroupByReturn[Properties, TReferences, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> GenerativeReturn[TProperties, None, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> GenerativeGroupByReturn[TProperties, None, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> GenerativeReturn[TProperties, CrossReferences, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> GenerativeGroupByReturn[TProperties, CrossReferences, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> GenerativeReturn[TProperties, TReferences, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> GenerativeGroupByReturn[TProperties, TReferences, None]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> GenerativeReturn[Properties, None, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> GenerativeGroupByReturn[Properties, None, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> GenerativeReturn[Properties, CrossReferences, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> GenerativeGroupByReturn[Properties, CrossReferences, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> GenerativeReturn[Properties, TReferences, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> GenerativeGroupByReturn[Properties, TReferences, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> GenerativeReturn[TProperties, None, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> GenerativeGroupByReturn[TProperties, None, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> GenerativeReturn[TProperties, CrossReferences, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> GenerativeGroupByReturn[TProperties, CrossReferences, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> GenerativeReturn[TProperties, TReferences, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> GenerativeGroupByReturn[TProperties, TReferences, Vectors]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> Union[
        GenerativeReturn[Properties, None, None], GenerativeReturn[Properties, None, Vectors]
    ]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> Union[
        GenerativeGroupByReturn[Properties, None, None],
        GenerativeGroupByReturn[Properties, None, Vectors],
    ]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> Union[
        GenerativeReturn[Properties, CrossReferences, None],
        GenerativeReturn[Properties, CrossReferences, Vectors],
    ]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> Union[
        GenerativeGroupByReturn[Properties, CrossReferences, None],
        GenerativeGroupByReturn[Properties, CrossReferences, Vectors],
    ]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> Union[
        GenerativeReturn[Properties, TReferences, None],
        GenerativeReturn[Properties, TReferences, Vectors],
    ]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> Union[
        GenerativeGroupByReturn[Properties, TReferences, None],
        GenerativeGroupByReturn[Properties, TReferences, Vectors],
    ]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> Union[
        GenerativeReturn[TProperties, None, None], GenerativeReturn[TProperties, None, Vectors]
    ]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> Union[
        GenerativeGroupByReturn[TProperties, None, None],
        GenerativeGroupByReturn[TProperties, None, Vectors],
    ]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> Union[
        GenerativeReturn[TProperties, CrossReferences, None],
        GenerativeReturn[TProperties, CrossReferences, Vectors],
    ]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> Union[
        GenerativeGroupByReturn[TProperties, CrossReferences, None],
        GenerativeGroupByReturn[TProperties, CrossReferences, Vectors],
    ]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: Literal[None] = None,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> Union[
        GenerativeReturn[TProperties, TReferences, None],
        GenerativeReturn[TProperties, TReferences, Vectors],
    ]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        group_by: GroupBy,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> Union[
        GenerativeGroupByReturn[TProperties, TReferences, None],
        GenerativeGroupByReturn[TProperties, TReferences, Vectors],
    ]: ...
