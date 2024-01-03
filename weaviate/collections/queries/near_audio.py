from io import BufferedReader
from pathlib import Path
from typing import Generic, List, Literal, Optional, Type, Union, overload

from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, Rerank
from weaviate.collections.classes.internal import (
    _Generative,
    _GenerativeReturn,
    _GroupBy,
    _GroupByReturn,
    _QueryReturn,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
    References,
    CrossReferences,
    TReferences,
)
from weaviate.collections.classes.types import (
    Properties,
    TProperties,
)
from weaviate.collections.queries.base import _BaseQuery


class _NearAudioQuery(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> _QueryReturn[Properties, References]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> _QueryReturn[Properties, CrossReferences]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> _QueryReturn[Properties, TReferences]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> _QueryReturn[TProperties, References]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> _QueryReturn[TProperties, CrossReferences]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> _QueryReturn[TProperties, TReferences]:
        ...

    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> Union[
        _QueryReturn[Properties, References],
        _QueryReturn[Properties, CrossReferences],
        _QueryReturn[Properties, TReferences],
        _QueryReturn[TProperties, References],
        _QueryReturn[TProperties, CrossReferences],
        _QueryReturn[TProperties, TReferences],
    ]:
        """Search for objects by audio in this collection using an audio-capable vectorisation module and vector-based similarity search.

        See the [docs](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/multi2vec-bind) for a more detailed explanation.

        NOTE:
            You must have an audio-capable vectorisation module installed in order to use this method, e.g. `multi2vec-bind`.

        Arguments:
            `near_audio`
                The audio file to search on, REQUIRED. This can be a base64 encoded string of the binary, a path to the file, or a file-like object.
            `certainty`
                The minimum similarity score to return. If not specified, the default certainty specified by the server is used.
            `distance`
                The maximum distance to search. If not specified, the default distance specified by the server is used.
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            `auto_limit`
                The maximum number of [autocut](https://weaviate.io/developers/weaviate/api/graphql/additional-operators#autocut) results to return. If not specified, no limit is applied.
            `filters`
                The filters to apply to the search.
            `rerank`
                How the results should be reranked. NOTE: A `rerank-*` module must be enabled for this functionality to work.
            `include_vector`
                Whether to include the vector in the results. If not specified, this is set to False.
            `return_metadata`
                The metadata to return for each object, defaults to `None`.
            `return_properties`
                The properties to return for each object.
            `return_references`
                The references to return for each object.

        NOTE:
            - If `return_properties` is not provided then all properties are returned except for blob properties.
            - If `return_metadata` is not provided then no metadata is provided.
            - If `return_references` is not provided then no references are provided.

        Returns:
            A `_QueryReturn` object that includes the searched objects.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If the request to the Weaviate server fails.
        """
        res = self._query().near_audio(
            audio=self._parse_media(near_audio),
            certainty=certainty,
            distance=distance,
            filters=filters,
            limit=limit,
            autocut=auto_limit,
            rerank=rerank,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(return_references),
        )
        return self._result_to_query_return(
            res,
            _QueryOptions.from_input(
                return_metadata,
                return_properties,
                include_vector,
                self._references,
                return_references,
                rerank,
            ),
            return_properties,
            return_references,
        )


class _NearAudioGenerate(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> _GenerativeReturn[Properties, References]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> _GenerativeReturn[Properties, CrossReferences]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> _GenerativeReturn[Properties, TReferences]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> _GenerativeReturn[TProperties, References]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> _GenerativeReturn[TProperties, CrossReferences]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> _GenerativeReturn[TProperties, TReferences]:
        ...

    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> Union[
        _GenerativeReturn[Properties, References],
        _GenerativeReturn[Properties, CrossReferences],
        _GenerativeReturn[Properties, TReferences],
        _GenerativeReturn[TProperties, References],
        _GenerativeReturn[TProperties, CrossReferences],
        _GenerativeReturn[TProperties, TReferences],
    ]:
        """Perform retrieval-augmented generation (RaG) on the results of a by-audio object search in this collection using an audio-capable vectorisation module and vector-based similarity search.

        See the [docs](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/multi2vec-bind) for a more detailed explanation.

        NOTE:
            You must have an audio-capable vectorisation module installed in order to use this method, e.g. `multi2vec-bind`.

        Arguments:
            `near_audio`
                The audio file to search on, REQUIRED. This can be a base64 encoded string of the binary, a path to the file, or a file-like object.
            `certainty`
                The minimum similarity score to return. If not specified, the default certainty specified by the server is used.
            `distance`
                The maximum distance to search. If not specified, the default distance specified by the server is used.
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            `auto_limit`
                The maximum number of [autocut](https://weaviate.io/developers/weaviate/api/graphql/additional-operators#autocut) results to return. If not specified, no limit is applied.
            `filters`
                The filters to apply to the search.
            `rerank`
                How the results should be reranked. NOTE: A `rerank-*` module must be enabled for this functionality to work.
            `include_vector`
                Whether to include the vector in the results. If not specified, this is set to False.
            `return_metadata`
                The metadata to return for each object, defaults to `None`.
            `return_properties`
                The properties to return for each object.
            `return_references`
                The references to return for each object.

        NOTE:
            - If `return_properties` is not provided then all properties are returned except for blob properties.
            - If `return_metadata` is not provided then no metadata is provided.
            - If `return_references` is not provided then no references are provided.

        Returns:
            A `_GenerativeReturn` object that includes the searched objects with per-object generated results and group generated results.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If the request to the Weaviate server fails.
        """
        res = self._query().near_audio(
            audio=self._parse_media(near_audio),
            certainty=certainty,
            distance=distance,
            filters=filters,
            rerank=rerank,
            generative=_Generative(
                single=single_prompt,
                grouped=grouped_task,
                grouped_properties=grouped_properties,
            ),
            limit=limit,
            autocut=auto_limit,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(return_references),
        )
        return self._result_to_generative_return(
            res,
            _QueryOptions.from_input(
                return_metadata,
                return_properties,
                include_vector,
                self._references,
                return_references,
                rerank,
            ),
            return_properties,
            return_references,
        )


class _NearAudioGroupBy(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> _GroupByReturn[Properties, References]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> _GroupByReturn[Properties, CrossReferences]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> _GroupByReturn[Properties, TReferences]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> _GroupByReturn[TProperties, References]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> _GroupByReturn[TProperties, CrossReferences]:
        ...

    @overload
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> _GroupByReturn[TProperties, TReferences]:
        ...

    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        group_by_property: str,
        number_of_groups: int,
        objects_per_group: int,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> Union[
        _GroupByReturn[Properties, References],
        _GroupByReturn[Properties, CrossReferences],
        _GroupByReturn[Properties, TReferences],
        _GroupByReturn[TProperties, References],
        _GroupByReturn[TProperties, CrossReferences],
        _GroupByReturn[TProperties, TReferences],
    ]:
        """Group the results of a by-audio object search in this collection using an audio-capable vectorisation module and vector-based similarity search.

        See the [docs](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/multi2vec-bind) for a more detailed explanation.

        NOTE:
            You must have an audio-capable vectorisation module installed in order to use this method, e.g. `multi2vec-bind`.

        Arguments:
            `near_audio`
                The audio file to search on, REQUIRED. This can be a base64 encoded string of the binary, a path to the file, or a file-like object.
            `group_by_property`
                The property to group by, REQUIRED.
            `number_of_groups`
                The number of groups to return, REQUIRED.
            `objects_per_group`
                The number of objects to return per group, REQUIRED.
            `certainty`
                The minimum similarity score to return. If not specified, the default certainty specified by the server is used.
            `distance`
                The maximum distance to search. If not specified, the default distance specified by the server is used.
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            `auto_limit`
                The maximum number of [autocut](https://weaviate.io/developers/weaviate/api/graphql/additional-operators#autocut) results to return. If not specified, no limit is applied.
            `filters`
                The filters to apply to the search.
            `include_vector`
                Whether to include the vector in the results. If not specified, this is set to False.
            `return_metadata`
                The metadata to return for each object, defaults to `None`.
            `return_properties`
                The properties to return for each object.
            `return_references`
                The references to return for each object.

        NOTE:
            - If `return_properties` is not provided then all properties are returned except for blob properties.
            - If `return_metadata` is not provided then no metadata is provided.
            - If `return_references` is not provided then no references are provided.

        Returns:
            A `_GroupByReturn` object that includes the searched objects grouped by the specified property.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If the request to the Weaviate server fails.
        """
        res = self._query().near_audio(
            audio=self._parse_media(near_audio),
            certainty=certainty,
            distance=distance,
            filters=filters,
            group_by=_GroupBy(
                prop=group_by_property,
                number_of_groups=number_of_groups,
                objects_per_group=objects_per_group,
            ),
            limit=limit,
            autocut=auto_limit,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(return_references),
        )
        return self._result_to_groupby_return(
            res,
            _QueryOptions.from_input(
                return_metadata,
                return_properties,
                include_vector,
                self._references,
                return_references,
            ),
            return_properties,
            return_references,
        )
