from io import BufferedReader
from pathlib import Path
from typing import Generic, Literal, Optional, Type, Union, overload
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, GroupBy, Rerank
from weaviate.collections.classes.internal import QueryReturn, GroupByReturn, CrossReferences
from weaviate.collections.classes.types import (
    Properties,
    TProperties,
    References,
    TReferences,
    Vectors,
)
from weaviate.collections.queries.base import _BaseQuery

class _NearImageQuery(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[Properties, None, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[Properties, None, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[Properties, CrossReferences, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[Properties, CrossReferences, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[Properties, TReferences, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[Properties, TReferences, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[TProperties, None, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[TProperties, None, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[TProperties, CrossReferences, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[TProperties, CrossReferences, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[TProperties, TReferences, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[TProperties, TReferences, None]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[Properties, None, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[Properties, None, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[Properties, CrossReferences, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[Properties, CrossReferences, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[Properties, TReferences, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[Properties, TReferences, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[TProperties, None, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[TProperties, None, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[TProperties, CrossReferences, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[TProperties, CrossReferences, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> QueryReturn[TProperties, TReferences, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> GroupByReturn[TProperties, TReferences, Vectors]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> Union[QueryReturn[Properties, None, None], QueryReturn[Properties, None, Vectors]]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> Union[GroupByReturn[Properties, None, None], GroupByReturn[Properties, None, Vectors]]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
        QueryReturn[Properties, CrossReferences, None],
        QueryReturn[Properties, CrossReferences, Vectors],
    ]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
        GroupByReturn[Properties, CrossReferences, None],
        GroupByReturn[Properties, CrossReferences, Vectors],
    ]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
        QueryReturn[Properties, TReferences, None], QueryReturn[Properties, TReferences, Vectors]
    ]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
        GroupByReturn[Properties, TReferences, None],
        GroupByReturn[Properties, TReferences, Vectors],
    ]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
    ) -> Union[QueryReturn[TProperties, None, None], QueryReturn[TProperties, None, Vectors]]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
        GroupByReturn[TProperties, None, None], GroupByReturn[TProperties, None, Vectors]
    ]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
        QueryReturn[TProperties, CrossReferences, None],
        QueryReturn[TProperties, CrossReferences, Vectors],
    ]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
        GroupByReturn[TProperties, CrossReferences, None],
        GroupByReturn[TProperties, CrossReferences, Vectors],
    ]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
        QueryReturn[TProperties, TReferences, None], QueryReturn[TProperties, TReferences, Vectors]
    ]: ...
    @overload
    def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
        *,
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
        GroupByReturn[TProperties, TReferences, None],
        GroupByReturn[TProperties, TReferences, Vectors],
    ]: ...
