from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from pydantic import Field

from weaviate.collection.classes.types import WeaviateInput
from weaviate.util import BaseEnum
from weaviate.types import UUID


class HybridFusion(str, BaseEnum):
    RANKED = "FUSION_TYPE_RANKED"
    RELATIVE_SCORE = "FUSION_TYPE_RELATIVE_SCORE"


class Move:
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
    def objects_list(self) -> Optional[List[str]]:
        return self.__objects

    @property
    def concepts_list(self) -> Optional[List[str]]:
        return self.__concepts


class MetadataQuery(WeaviateInput):
    uuid: bool = Field(default=False)
    vector: bool = Field(default=False)
    creation_time_unix: bool = Field(default=False)
    last_update_time_unix: bool = Field(default=False)
    distance: bool = Field(default=False)
    certainty: bool = Field(default=False)
    score: bool = Field(default=False)
    explain_score: bool = Field(default=False)
    is_consistent: bool = Field(default=False)


class Generate(WeaviateInput):
    single_prompt: Optional[str] = Field(default=None)
    grouped_task: Optional[str] = Field(default=None)
    grouped_properties: Optional[List[str]] = Field(default=None)


class Sort(WeaviateInput):
    prop: str
    ascending: bool = Field(default=True)


class GroupBy(WeaviateInput):
    prop: str
    number_of_groups: int
    objects_per_group: int


class FromReference(WeaviateInput):
    link_on: str
    return_properties: Optional["PROPERTIES"] = Field(default=None)
    return_metadata: Optional[MetadataQuery] = Field(default=None)

    def __hash__(self) -> int:  # for set
        return hash(str(self))


class FromReferenceMultiTarget(FromReference):
    target_collection: str


PROPERTY = Union[str, FromReference]
PROPERTIES = Union[List[PROPERTY], PROPERTY]


@dataclass
class RefProps:
    meta: MetadataQuery
    refs: Dict[str, "RefProps"]
