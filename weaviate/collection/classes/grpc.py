from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from weaviate.util import BaseEnum
from weaviate.weaviate_types import UUID


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


class MetadataQuery(BaseModel):
    uuid: bool = False
    vector: bool = False
    creation_time_unix: bool = False
    last_update_time_unix: bool = False
    distance: bool = False
    certainty: bool = False
    score: bool = False
    explain_score: bool = False
    is_consistent: bool = False


class Sort(BaseModel):
    prop: str
    ascending: bool = True


class LinkTo(BaseModel):
    link_on: str
    properties: Optional["PROPERTIES"] = Field(default=None)
    metadata: Optional[MetadataQuery] = Field(default=None)

    def __hash__(self) -> int:  # for set
        return hash(str(self))


class LinkToMultiTarget(LinkTo):
    target_collection: str


PROPERTIES = Union[List[Union[str, LinkTo]], str]


@dataclass
class RefProps:
    meta: MetadataQuery
    refs: Dict[str, "RefProps"]
