from dataclasses import dataclass
from typing import List, Literal, Optional, Union

from pydantic import Field

from weaviate.collections.classes.types import _WeaviateInput
from weaviate.util import BaseEnum
from weaviate.types import UUID


class HybridFusion(str, BaseEnum):
    """Define how the query's hybrid fusion operation should be performed."""

    RANKED = "FUSION_TYPE_RANKED"
    RELATIVE_SCORE = "FUSION_TYPE_RELATIVE_SCORE"


class Move:
    """Define how the query's move operation should be performed."""

    def __init__(
        self,
        force: float,
        objects: Optional[Union[List[UUID], UUID]] = None,
        concepts: Optional[Union[List[str], str]] = None,
    ):
        if (objects is None or (isinstance(objects, list) and len(objects) == 0)) and (
            concepts is None or (isinstance(concepts, list) and len(concepts) == 0)
        ):
            raise ValueError("Either objects or concepts need to be given")

        self.force = force

        # accept single values, but make them a list
        if objects is None:
            self.__objects = None
        elif not isinstance(objects, list):
            self.__objects = [str(objects)]
        else:
            self.__objects = [str(obj_uuid) for obj_uuid in objects]

        if concepts is None:
            self.__concepts = None
        elif not isinstance(concepts, list):
            self.__concepts = [concepts]
        else:
            self.__concepts = concepts

    @property
    def _objects_list(self) -> Optional[List[str]]:
        return self.__objects

    @property
    def _concepts_list(self) -> Optional[List[str]]:
        return self.__concepts

    def _to_gql_payload(self) -> dict:
        payload: dict = {"force": self.force}
        if self.__objects is not None:
            payload["objects"] = self.__objects
        if self.__concepts is not None:
            payload["concepts"] = self.__concepts
        return payload


class MetadataQuery(_WeaviateInput):
    """Define which metadata should be returned in the query's results."""

    creation_time: bool = Field(default=False)
    last_update_time: bool = Field(default=False)
    distance: bool = Field(default=False)
    certainty: bool = Field(default=False)
    score: bool = Field(default=False)
    explain_score: bool = Field(default=False)
    is_consistent: bool = Field(default=False)

    @classmethod
    def _full(cls) -> "MetadataQuery":
        """Return a MetadataQuery with all fields set to True."""
        return cls(
            creation_time=True,
            last_update_time=True,
            distance=True,
            certainty=True,
            score=True,
            explain_score=True,
            is_consistent=True,
        )


@dataclass
class _MetadataQuery:
    vector: bool
    uuid: bool = True
    creation_time_unix: bool = False
    last_update_time_unix: bool = False
    distance: bool = False
    certainty: bool = False
    score: bool = False
    explain_score: bool = False
    is_consistent: bool = False

    @classmethod
    def from_public(cls, public: Optional[MetadataQuery], include_vector: bool) -> "_MetadataQuery":
        return (
            cls(
                vector=include_vector,
            )
            if public is None
            else cls(
                vector=include_vector,
                creation_time_unix=public.creation_time,
                last_update_time_unix=public.last_update_time,
                distance=public.distance,
                certainty=public.certainty,
                score=public.score,
                explain_score=public.explain_score,
                is_consistent=public.is_consistent,
            )
        )


METADATA = Union[
    List[
        Literal[
            "creation_time_unix",
            "last_update_time_unix",
            "distance",
            "certainty",
            "score",
            "explain_score",
            "is_consistent",
        ]
    ],
    MetadataQuery,
]


class Generate(_WeaviateInput):
    """Define how the query's RAG capabilities should be performed."""

    single_prompt: Optional[str] = Field(default=None)
    grouped_task: Optional[str] = Field(default=None)
    grouped_properties: Optional[List[str]] = Field(default=None)


class Sort(_WeaviateInput):
    """Define how the query's sort operation should be performed."""

    prop: str
    ascending: bool = Field(default=True)


class QueryReference(_WeaviateInput):
    """Define a query-time reference to a single-target property when querying through cross-references."""

    link_on: str
    include_vector: bool = Field(default=False)
    return_metadata: Optional[MetadataQuery] = Field(default=None)
    return_properties: Optional["PROPERTIES"] = Field(default=None)
    return_references: Optional["REFERENCES"] = Field(default=None)

    def __hash__(self) -> int:  # for set
        return hash(str(self))

    @property
    def _return_metadata(self) -> _MetadataQuery:
        return _MetadataQuery.from_public(self.return_metadata, self.include_vector)


class QueryReferenceMultiTarget(QueryReference):
    """Define a query-time reference to a multi-target property when querying through cross-references."""

    target_collection: str


class QueryNested(_WeaviateInput):
    """Define the query-time return properties of a nested property."""

    name: str
    properties: "PROPERTIES"

    def __hash__(self) -> int:  # for set
        return hash(str(self))


# deprecated and should be removed in v4 GA
FromReference = QueryReference
"""@deprecated: Use `QueryReference` instead."""
FromReferenceMultiTarget = QueryReferenceMultiTarget
"""@deprecated: Use `QueryReferenceMultiTarget` instead."""
FromNested = QueryNested
"""@deprecated: Use `QueryNested` instead."""

REFERENCE = Union[
    FromReference, FromReferenceMultiTarget, QueryReference, QueryReferenceMultiTarget
]
REFERENCES = Union[List[REFERENCE], REFERENCE]

PROPERTY = Union[str, FromNested, QueryNested]
PROPERTIES = Union[List[PROPERTY], PROPERTY]

NestedProperties = Union[List[Union[str, FromNested, QueryNested]], str, FromNested, QueryNested]

_PROPERTY = Union[PROPERTY, REFERENCE]
_PROPERTIES = Union[PROPERTIES, REFERENCES]
