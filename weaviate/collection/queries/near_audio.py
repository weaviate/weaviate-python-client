from io import BufferedReader
from pathlib import Path
from typing import List, Optional, Type, Union

from weaviate.collection.classes.filters import (
    _Filters,
)
from weaviate.collection.classes.grpc import (
    MetadataQuery,
    PROPERTIES,
)
from weaviate.collection.classes.internal import (
    _Generative,
    _GenerativeReturn,
    _GroupBy,
    _GroupByReturn,
    _QueryReturn,
)
from weaviate.collection.classes.types import (
    Properties,
)
from weaviate.collection.queries.base import _Grpc


class _NearAudioQuery(_Grpc):
    def near_audio(
        self,
        near_audio: Union[str, Path, BufferedReader],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        ret_properties, ret_type = self._determine_generic(return_properties)
        res = self._query().near_audio(
            audio=self._parse_media(near_audio),
            certainty=certainty,
            distance=distance,
            filters=filters,
            limit=limit,
            autocut=auto_limit,
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        return self._result_to_query_return(res, ret_type)


class _NearAudioGenerate(_Grpc):
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
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GenerativeReturn[Properties]:
        ret_properties, ret_type = self._determine_generic(return_properties)
        res = self._query().near_audio(
            audio=self._parse_media(near_audio),
            certainty=certainty,
            distance=distance,
            filters=filters,
            generative=_Generative(
                single=single_prompt,
                grouped=grouped_task,
                grouped_properties=grouped_properties,
            ),
            limit=limit,
            autocut=auto_limit,
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        return self._result_to_generative_return(res, ret_type)


class _NearAudioGroupBy(_Grpc):
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
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GroupByReturn[Properties]:
        ret_properties, ret_type = self._determine_generic(return_properties)
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
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        return self._result_to_groupby_return(res, ret_type)
