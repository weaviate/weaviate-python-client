from typing import List, Optional, Union

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

    uuid: bool = Field(default=False)
    vector: bool = Field(default=False)
    creation_time_unix: bool = Field(default=False)
    last_update_time_unix: bool = Field(default=False)
    distance: bool = Field(default=False)
    certainty: bool = Field(default=False)
    score: bool = Field(default=False)
    explain_score: bool = Field(default=False)
    is_consistent: bool = Field(default=False)

    @classmethod
    def _full(cls) -> "MetadataQuery":
        """Return a MetadataQuery with all fields set to True except for vector."""
        return cls(
            uuid=True,
            creation_time_unix=True,
            last_update_time_unix=True,
            distance=True,
            certainty=True,
            score=True,
            explain_score=True,
            is_consistent=True,
        )


class Generate(_WeaviateInput):
    """Define how the query's RAG capabilities should be performed."""

    single_prompt: Optional[str] = Field(default=None)
    grouped_task: Optional[str] = Field(default=None)
    grouped_properties: Optional[List[str]] = Field(default=None)


class Sort(_WeaviateInput):
    """Define how the query's sort operation should be performed."""

    prop: str
    ascending: bool = Field(default=True)


class FromReference(_WeaviateInput):
    """Define a query-time reference to a single-target property when querying through cross-references."""

    link_on: str
    return_properties: Optional["PROPERTIES"] = Field(default=None)
    return_metadata: Optional[MetadataQuery] = Field(default=None)

    def __hash__(self) -> int:  # for set
        return hash(str(self))


class FromReferenceMultiTarget(FromReference):
    """Define a query-time reference to a multi-target property when querying through cross-references."""

    target_collection: str


class FromNested(_WeaviateInput):
    """Define the return properties of a nested property."""

    name: str
    properties: "NestedProperties"

    def __hash__(self) -> int:  # for set
        return hash(str(self))


PROPERTY = Union[str, FromReference, FromNested]
PROPERTIES = Union[List[PROPERTY], PROPERTY]

NestedProperties = Union[List[Union[str, FromNested]], str, FromNested]
