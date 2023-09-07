from dataclasses import dataclass
from typing import Dict, Generic, List, Optional, Type, Union

from pydantic import BaseModel, ConfigDict, Field

from weaviate.collection.classes.filters import _Filters
from weaviate.collection.classes.types import P
from weaviate.util import BaseEnum
from weaviate.weaviate_types import UUID


class HybridFusion(str, BaseEnum):
    RANKED = "FUSION_TYPE_RANKED"
    RELATIVE_SCORE = "FUSION_TYPE_RELATIVE_SCORE"


class Options(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    filters: Optional[_Filters] = Field(default=None)
    limit: Optional[int] = Field(default=None)


class HybridOptions(Options):
    alpha: Optional[float] = Field(default=None)
    vector: Optional[List[float]] = Field(default=None)
    properties: Optional[List[str]] = Field(default=None)
    fusion_type: Optional[HybridFusion] = Field(default=None)
    auto_limit: Optional[int] = Field(default=None)


class GetOptions(Options):
    offset: Optional[int] = Field(default=None)
    after: Optional[UUID] = Field(default=None)


class BM25Options(Options):
    properties: Optional[List[str]] = Field(default=None)
    auto_limit: Optional[int] = Field(default=None)


class NearMediaOptions(Options):
    certainty: Optional[float] = Field(default=None)
    distance: Optional[float] = Field(default=None)
    auto_limit: Optional[int] = Field(default=None)


class NearVectorOptions(NearMediaOptions):
    pass


class NearObjectOptions(NearMediaOptions):
    pass


class NearTextOptions(NearMediaOptions):
    move_to: Optional["Move"] = Field(default=None)
    move_away: Optional["Move"] = Field(default=None)
    filters: Optional[_Filters] = Field(default=None)


class NearImageOptions(NearMediaOptions):
    pass


class NearAudioOptions(NearMediaOptions):
    pass


class NearVideoOptions(NearMediaOptions):
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
class MetadataQuery:
    uuid: bool = False
    vector: bool = False
    creation_time_unix: bool = False
    last_update_time_unix: bool = False
    distance: bool = False
    certainty: bool = False
    score: bool = False
    explain_score: bool = False
    is_consistent: bool = False


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
class ReturnValues(Generic[P]):
    properties: Optional[Union[PROPERTIES, Type[P]]] = None
    metadata: Optional[MetadataQuery] = None


@dataclass
class RefProps:
    meta: MetadataQuery
    refs: Dict[str, "RefProps"]
