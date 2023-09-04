from dataclasses import dataclass
from typing import Dict, List, Optional, Type, Union

from pydantic import BaseModel

from weaviate.collection.classes.filters import _Filters
from weaviate.collection.classes.types import Properties
from weaviate.util import BaseEnum
from weaviate.weaviate_types import UUID


class HybridFusion(str, BaseEnum):
    RANKED = "FUSION_TYPE_RANKED"
    RELATIVE_SCORE = "FUSION_TYPE_RELATIVE_SCORE"


@dataclass
class Options:
    filters: Optional[_Filters] = None


@dataclass
class HybridOptions(Options):
    alpha: Optional[float] = None
    vector: Optional[List[float]] = None
    properties: Optional[List[str]] = None
    fusion_type: Optional[HybridFusion] = None
    limit: Optional[int] = None
    auto_limit: Optional[int] = None


@dataclass
class GetOptions(Options):
    limit: Optional[int] = None
    offset: Optional[int] = None
    after: Optional[UUID] = None


@dataclass
class BM25Options(Options):
    properties: Optional[List[str]] = None
    limit: Optional[int] = None
    auto_limit: Optional[int] = None


@dataclass
class NearMediaOptions(Options):
    certainty: Optional[float] = None
    distance: Optional[float] = None
    auto_limit: Optional[int] = None


@dataclass
class NearVectorOptions(NearMediaOptions):
    pass


@dataclass
class NearObjectOptions(NearMediaOptions):
    pass


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


@dataclass
class NearTextOptions(NearMediaOptions):
    move_to: Optional[Move] = None
    move_away: Optional[Move] = None
    filters: Optional[_Filters] = None


@dataclass
class NearImageOptions(NearMediaOptions):
    pass


@dataclass
class NearAudioOptions(NearMediaOptions):
    pass


@dataclass
class NearVideoOptions(NearMediaOptions):
    pass


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
    properties: Optional[Union[PROPERTIES, Type[Properties]]] = None
    metadata: Optional[MetadataQuery] = None


@dataclass
class RefProps:
    meta: MetadataQuery
    refs: Dict[str, "RefProps"]
