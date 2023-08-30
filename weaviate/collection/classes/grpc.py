from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from pydantic import BaseModel

from weaviate.collection.classes.filters import _Filters
from weaviate.util import BaseEnum
from weaviate.weaviate_types import UUID


class HybridFusion(str, BaseEnum):
    RANKED = "FUSION_TYPE_RANKED"
    RELATIVE_SCORE = "FUSION_TYPE_RELATIVE_SCORE"


@dataclass
class HybridOptions:
    alpha: Optional[float] = None
    vector: Optional[List[float]] = None
    properties: Optional[List[str]] = None
    fusion_type: Optional[HybridFusion] = None
    limit: Optional[int] = None
    autocut: Optional[int] = None


@dataclass
class GetOptions:
    limit: Optional[int] = None
    offset: Optional[int] = None
    after: Optional[UUID] = None


@dataclass
class BM25Options:
    properties: Optional[List[str]] = None
    limit: Optional[int] = None
    autocut: Optional[int] = None


@dataclass
class NearVectorOptions:
    certainty: Optional[float] = None
    distance: Optional[float] = None
    autocut: Optional[int] = None


@dataclass
class NearObjectOptions:
    certainty: Optional[float] = None
    distance: Optional[float] = None
    autocut: Optional[int] = None


@dataclass
class Move:
    force: float
    objects: Optional[Union[List[UUID], UUID]] = None
    concepts: Optional[Union[List[str], str]] = None

    def __post_init__(self):
        if (
            self.objects is None or (isinstance(self.objects, list) and len(self.objects) == 0)
        ) and (
            self.concepts is None
            or (isinstance(self.concepts, list) and len(self.concepts) == 0) == 0
        ):
            raise ValueError("Either objects or concepts need to be given")

        # accept single values, but make them a list
        if self.objects is None:
            self.__objects = None
        elif not isinstance(self.objects, list):
            self.__objects = [str(self.objects)]
        else:
            self.__objects = [str(obj_uuid) for obj_uuid in self.objects]

        if self.concepts is None:
            self.__concepts = None
        elif not isinstance(self.concepts, list):
            self.__concepts = [self.concepts]
        else:
            self.__concepts = self.concepts

    @property
    def objects_list(self) -> Optional[List[str]]:
        return self.__objects

    @property
    def concepts_list(self) -> Optional[List[str]]:
        return self.__concepts


@dataclass
class NearTextOptions:
    certainty: Optional[float] = None
    distance: Optional[float] = None
    move_to: Optional[Move] = None
    move_away: Optional[Move] = None
    autocut: Optional[int] = None
    filters: Optional[_Filters] = None


@dataclass
class MetadataQuery:
    uuid: bool = False
    vector: bool = False
    creation_time_unix: bool = False
    last_update_time_unix: bool = False
    distance: bool = False
    certainty: bool = False
    score: bool = False
    explain_score: bool = False


class LinkTo(BaseModel):
    link_on: str
    properties: "PROPERTIES"
    metadata: MetadataQuery

    def __hash__(self) -> int:  # for set
        return hash(str(self))


class LinkToMultiTarget(LinkTo):
    target_collection: str


PROPERTIES = Union[List[Union[str, LinkTo]], str]


@dataclass
class ReturnValues:
    metadata: Optional[MetadataQuery] = None
    properties: Optional[PROPERTIES] = None


@dataclass
class RefProps:
    meta: MetadataQuery
    refs: Dict[str, "RefProps"]
