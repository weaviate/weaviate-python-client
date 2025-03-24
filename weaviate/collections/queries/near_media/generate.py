from typing import Generic, List, Optional, Union

from weaviate import syncify
from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.generative import (
    _GenerativeConfigRuntime,
    _GroupedTask,
    _SinglePrompt,
)
from weaviate.collections.classes.grpc import (
    METADATA,
    GroupBy,
    Rerank,
    NearMediaType,
    TargetVectorJoinType,
)
from weaviate.collections.classes.internal import (
    GenerativeSearchReturnType,
    ReturnProperties,
    ReturnReferences,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base import _BaseGenerate
from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync
from weaviate.types import BLOB_INPUT, NUMBER, INCLUDE_VECTOR


class _NearMediaGenerateAsync(
    Generic[Properties, References], _BaseGenerate[ConnectionAsync, Properties, References]
):
    async def near_media(
        self,
        media: BLOB_INPUT,
        media_type: NearMediaType,
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> GenerativeSearchReturnType[Properties, References, TProperties, TReferences]:
        """Perform retrieval-augmented generation (RAG) on the results of a by-audio object search in this collection using an audio-capable vectorization module and vector-based similarity search.

        See the [docs](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/multi2vec-bind) for a more detailed explanation.

        NOTE:
            You must have a multi-media-capable vectorization module installed in order to use this method, e.g. `multi2vec-bind`.

        Arguments:
            `near_media`
                The media file to search on, REQUIRED. This can be a base64 encoded string of the binary, a path to the file, or a file-like object.
            `media_type`
                The type of the provided media file, REQUIRED.
            `single_prompt`
                The prompt to use for generative query on each object individually.
            `grouped_task`
                The prompt to use for generative query on the entire result set.
            `grouped_properties`
                The properties to use in the generative query on the entire result set.
            `generative_provider`
                Specify the generative provider and provier-specific options with a suitable `GenerativeProvider.<provider>()` factory function.
            `certainty`
                The minimum similarity score to return. If not specified, the default certainty specified by the server is used.
            `distance`
                The maximum distance to search. If not specified, the default distance specified by the server is used.
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            `offset`
                The offset to start from. If not specified, the retrieval begins from the first object in the server.
            `auto_limit`
                The maximum number of [autocut](https://weaviate.io/developers/weaviate/api/graphql/additional-operators#autocut) results to return. If not specified, no limit is applied.
            `filters`
                The filters to apply to the search.
            `group_by`
                How the results should be grouped by a specific property.
            `rerank`
                How the results should be reranked. NOTE: A `rerank-*` module must be enabled for this functionality to work.
            `target_vector`
                The name of the vector space to search in for named vector configurations. Required if multiple spaces are configured.
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
            - If `return_metadata` is not provided then no metadata is provided. Use MetadataQuery.full() to retrieve all metadata.
            - If `return_references` is not provided then no references are provided.

        Returns:
            A `GenerativeReturn` or `GenerativeGroupByReturn` object that includes the searched objects.
            If `group_by` is provided then a `GenerativeGroupByReturn` object is returned, otherwise a `GenerativeReturn` object is returned.

        Raises:
            `weaviate.exceptions.WeaviateQueryError`:
                If the request to the Weaviate server fails.
        """
        return await aresult(
            self._executor.near_media(
                connection=self._connection,
                media=media,
                media_type=media_type,
                single_prompt=single_prompt,
                grouped_task=grouped_task,
                grouped_properties=grouped_properties,
                generative_provider=generative_provider,
                certainty=certainty,
                distance=distance,
                limit=limit,
                offset=offset,
                auto_limit=auto_limit,
                filters=filters,
                group_by=group_by,
                rerank=rerank,
                target_vector=target_vector,
                include_vector=include_vector,
                return_metadata=return_metadata,
                return_properties=return_properties,
                return_references=return_references,
            )
        )


@syncify.convert(_NearMediaGenerateAsync)
class _NearMediaGenerate(
    Generic[Properties, References], _BaseGenerate[ConnectionSync, Properties, References]
):
    pass
