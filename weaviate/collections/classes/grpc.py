from dataclasses import dataclass
from enum import Enum, auto
from typing import (
    ClassVar,
    Generic,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Type,
    Union,
    Dict,
    cast,
)
from typing_extensions import TypeGuard, TypeVar

from pydantic import ConfigDict, Field

from weaviate.collections.classes.types import _WeaviateInput
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import base_search_pb2
from weaviate.str_enum import BaseEnum
from weaviate.types import INCLUDE_VECTOR, UUID, NUMBER
from weaviate.util import _ServerVersion


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
            payload["objects"] = [{"id": obj} for obj in self.__objects]
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
    def full(cls) -> "MetadataQuery":
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
    vectors: Optional[List[str]] = None

    @classmethod
    def from_public(
        cls, public: Optional[MetadataQuery], include_vector: INCLUDE_VECTOR
    ) -> "_MetadataQuery":
        return (
            cls(
                vector=include_vector if isinstance(include_vector, bool) else False,
                vectors=include_vector if isinstance(include_vector, list) else None,
            )
            if public is None
            else cls(
                vector=include_vector if isinstance(include_vector, bool) else False,
                vectors=include_vector if isinstance(include_vector, list) else None,
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
            "creation_time",
            "last_update_time",
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


class GroupBy(_WeaviateInput):
    """Define how the query's group-by operation should be performed."""

    prop: str
    objects_per_group: int
    number_of_groups: int


class _Sort(_WeaviateInput):
    prop: str
    ascending: bool = Field(default=True)


class _Sorting:
    def __init__(self) -> None:
        self.sorts: List[_Sort] = []

    def by_property(self, name: str, ascending: bool = True) -> "_Sorting":
        """Sort by an object property in the collection."""
        self.sorts.append(_Sort(prop=name, ascending=ascending))
        return self

    def by_id(self, ascending: bool = True) -> "_Sorting":
        """Sort by an object's ID in the collection."""
        self.sorts.append(_Sort(prop="_id", ascending=ascending))
        return self

    def by_creation_time(self, ascending: bool = True) -> "_Sorting":
        """Sort by an object's creation time."""
        self.sorts.append(_Sort(prop="_creationTimeUnix", ascending=ascending))
        return self

    def by_update_time(self, ascending: bool = True) -> "_Sorting":
        """Sort by an object's last update time."""
        self.sorts.append(_Sort(prop="_lastUpdateTimeUnix", ascending=ascending))
        return self


Sorting = _Sorting
"""The type returned by the `Sort` class to be used when defining programmatic sort chains."""


class Sort:
    """Define how the query's sort operation should be performed using the available static methods."""

    def __init__(self) -> None:
        raise TypeError("Sort cannot be instantiated. Use the static methods to create a sorter.")

    @staticmethod
    def by_property(name: str, ascending: bool = True) -> Sorting:
        """Sort by an object property in the collection."""
        return _Sorting().by_property(name=name, ascending=ascending)

    @staticmethod
    def by_id(ascending: bool = True) -> Sorting:
        """Sort by an object's ID in the collection."""
        return _Sorting().by_id(ascending=ascending)

    @staticmethod
    def by_creation_time(ascending: bool = True) -> Sorting:
        """Sort by an object's creation time."""
        return _Sorting().by_creation_time(ascending=ascending)

    @staticmethod
    def by_update_time(ascending: bool = True) -> Sorting:
        """Sort by an object's last update time."""
        return _Sorting().by_update_time(ascending=ascending)


class Rerank(_WeaviateInput):
    """Define how the query's rerank operation should be performed."""

    prop: str
    query: Optional[str] = Field(default=None)


OneDimensionalVectorType = Sequence[NUMBER]
"""Represents a one-dimensional vector, e.g. one produced by `text2vec-jinaai`"""
TwoDimensionalVectorType = Sequence[Sequence[NUMBER]]
"""Represents a two-dimensional vector, e.g. one produced by `text2colbert-jinaai"""

PrimitiveVectorType = Union[OneDimensionalVectorType, TwoDimensionalVectorType]


V = TypeVar("V", OneDimensionalVectorType, TwoDimensionalVectorType)


class _ListOfVectorsQuery(_WeaviateInput, Generic[V]):
    dimensionality: Literal["1D", "2D"]
    vectors: Sequence[V]

    @staticmethod
    def is_one_dimensional(
        self_: "_ListOfVectorsQuery",
    ) -> TypeGuard["_ListOfVectorsQuery[OneDimensionalVectorType]"]:
        return self_.dimensionality == "1D"

    @staticmethod
    def is_two_dimensional(
        self_: "_ListOfVectorsQuery",
    ) -> TypeGuard["_ListOfVectorsQuery[TwoDimensionalVectorType]"]:
        return self_.dimensionality == "2D"


ListOfVectorsQuery = _ListOfVectorsQuery
"""Define a many-vectors query to be used within a near vector search, i.e. multiple vectors over a single-vector space."""


NearVectorInputType = Union[
    OneDimensionalVectorType,
    TwoDimensionalVectorType,
    Mapping[
        str,
        Union[
            OneDimensionalVectorType,
            TwoDimensionalVectorType,
            ListOfVectorsQuery[OneDimensionalVectorType],
            ListOfVectorsQuery[TwoDimensionalVectorType],
        ],
    ],
]
"""Define the input types that can be used in a near vector search"""


class NearVector:
    """Factory class to use when defining near vector queries with multiple vectors in `near_vector()` and `hybrid()` methods."""

    @staticmethod
    def list_of_vectors(*vectors: V) -> _ListOfVectorsQuery[V]:
        """Define a many-vectors query to be used within a near vector search, i.e. multiple vectors over a single-vector space."""
        if len(vectors) > 0 and len(vectors[0]) > 0:
            try:
                len(cast(Sequence[TwoDimensionalVectorType], vectors)[0][0])
                dimensionality: Literal["1D", "2D"] = "2D"
            except TypeError:
                dimensionality = "1D"
            return _ListOfVectorsQuery[V](dimensionality=dimensionality, vectors=vectors)
        else:
            raise WeaviateInvalidInputError(f"At least one vector must be given, got: {vectors}")


class _HybridNearBase(_WeaviateInput):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    distance: Optional[float] = None
    certainty: Optional[float] = None


class _HybridNearText(_HybridNearBase):
    text: Union[str, List[str]]
    move_to: Optional[Move] = None
    move_away: Optional[Move] = None


class _HybridNearVector:  # can't be a Pydantic model because of validation issues parsing numpy, pd, pl arrays/series
    vector: NearVectorInputType
    distance: Optional[float]
    certainty: Optional[float]

    def __init__(
        self,
        *,
        vector: NearVectorInputType,
        distance: Optional[float] = None,
        certainty: Optional[float] = None,
    ) -> None:
        self.vector = vector
        self.distance = distance
        self.certainty = certainty


HybridVectorType = Union[NearVectorInputType, _HybridNearText, _HybridNearVector]


class _MultiTargetVectorJoinEnum(BaseEnum):
    """Define how multi target vector searches should be combined."""

    SUM = auto()
    AVERAGE = auto()
    MINIMUM = auto()
    RELATIVE_SCORE = auto()
    MANUAL_WEIGHTS = auto()


@dataclass
class _MultiTargetVectorJoin:
    combination: _MultiTargetVectorJoinEnum
    target_vectors: List[str]
    weights: Optional[Dict[str, Union[float, List[float]]]] = None

    def to_grpc_target_vector(self, version: _ServerVersion) -> base_search_pb2.Targets:
        combination = self.combination
        if combination == _MultiTargetVectorJoinEnum.AVERAGE:
            combination_grpc = base_search_pb2.COMBINATION_METHOD_TYPE_AVERAGE
        elif combination == _MultiTargetVectorJoinEnum.SUM:
            combination_grpc = base_search_pb2.COMBINATION_METHOD_TYPE_SUM
        elif combination == _MultiTargetVectorJoinEnum.RELATIVE_SCORE:
            combination_grpc = base_search_pb2.COMBINATION_METHOD_TYPE_RELATIVE_SCORE
        elif combination == _MultiTargetVectorJoinEnum.MANUAL_WEIGHTS:
            combination_grpc = base_search_pb2.COMBINATION_METHOD_TYPE_MANUAL
        else:
            assert combination == _MultiTargetVectorJoinEnum.MINIMUM
            combination_grpc = base_search_pb2.COMBINATION_METHOD_TYPE_MIN

        if version.is_lower_than(1, 27, 0):
            if self.weights is not None and any(isinstance(w, list) for w in self.weights.values()):
                raise ValueError(
                    "Multiple weights per target are not supported in this Weaviate version. Please upgrade to at least Weaviate 1.27.0."
                )
            # mypy does not seem to understand the type narrowing right above
            weights_typed = cast(Optional[Dict[str, float]], self.weights)

            return base_search_pb2.Targets(
                target_vectors=self.target_vectors,
                weights=weights_typed,
                combination=combination_grpc,
            )
        else:
            weights: List[base_search_pb2.WeightsForTarget] = []
            target_vectors: List[str] = self.target_vectors
            if self.weights is not None:
                target_vectors = []
                for target, weight in self.weights.items():
                    if isinstance(weight, list):
                        for w in weight:
                            weights.append(
                                base_search_pb2.WeightsForTarget(target=target, weight=w)
                            )
                            target_vectors.append(target)
                    else:
                        weights.append(
                            base_search_pb2.WeightsForTarget(target=target, weight=weight)
                        )
                        target_vectors.append(target)

            return base_search_pb2.Targets(
                target_vectors=target_vectors,
                weights_for_targets=weights,
                combination=combination_grpc,
            )


TargetVectorJoinType = Union[str, List[str], _MultiTargetVectorJoin]


class TargetVectors:
    """Define how the distances from different target vectors should be combined using the available methods."""

    @staticmethod
    def sum(target_vectors: List[str]) -> _MultiTargetVectorJoin:  # noqa: A003
        """Combine the distance from different target vectors by summing them."""
        return _MultiTargetVectorJoin(
            combination=_MultiTargetVectorJoinEnum.SUM, target_vectors=target_vectors
        )

    @staticmethod
    def average(target_vectors: List[str]) -> _MultiTargetVectorJoin:
        """Combine the distance from different target vectors by averaging them."""
        return _MultiTargetVectorJoin(
            combination=_MultiTargetVectorJoinEnum.AVERAGE, target_vectors=target_vectors
        )

    @staticmethod
    def minimum(target_vectors: List[str]) -> _MultiTargetVectorJoin:
        """Combine the distance from different target vectors by using the minimum distance."""
        return _MultiTargetVectorJoin(
            combination=_MultiTargetVectorJoinEnum.MINIMUM, target_vectors=target_vectors
        )

    @staticmethod
    def manual_weights(weights: Dict[str, Union[float, List[float]]]) -> _MultiTargetVectorJoin:
        """Combine the distance from different target vectors by summing them using manual weights."""
        return _MultiTargetVectorJoin(
            combination=_MultiTargetVectorJoinEnum.MANUAL_WEIGHTS,
            target_vectors=list(weights.keys()),
            weights=weights,
        )

    @staticmethod
    def relative_score(weights: Dict[str, Union[float, List[float]]]) -> _MultiTargetVectorJoin:
        """Combine the distance from different target vectors using score fusion."""
        return _MultiTargetVectorJoin(
            combination=_MultiTargetVectorJoinEnum.RELATIVE_SCORE,
            target_vectors=list(weights.keys()),
            weights=weights,
        )


class HybridVector:
    """Use this factory class to define the appropriate classes needed when defining near text and near vector sub-searches in hybrid queries."""

    @staticmethod
    def near_text(
        query: Union[str, List[str]],
        *,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
    ) -> _HybridNearText:
        """Define a near text search to be used within a hybrid query.

        Arguments:
            `query`
                The text to search for as a string or a list of strings.
            `certainty`
                The minimum similarity score to return. If not specified, the default certainty specified by the server is used.
            `distance`
                The maximum distance to search. If not specified, the default distance specified by the server is used.
            `move_to`
                Define the concepts that should be moved towards in the vector space during the search.
            `move_away`
                Define the concepts that should be moved away from in the vector space during the search.

        Returns:
            A `_HybridNearText` object to be used in the `vector` parameter of the `query.hybrid` and `generate.hybrid` search methods.
        """
        return _HybridNearText(
            text=query,
            distance=distance,
            certainty=certainty,
            move_to=move_to,
            move_away=move_away,
        )

    @staticmethod
    def near_vector(
        vector: NearVectorInputType,
        *,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
    ) -> _HybridNearVector:
        """Define a near vector search to be used within a hybrid query.

        Arguments:
            `certainty`
                The minimum similarity score to return. If not specified, the default certainty specified by the server is used.
            `distance`
                The maximum distance to search. If not specified, the default distance specified by the server is used.

        Returns:
            A `_HybridNearVector` object to be used in the `vector` parameter of the `query.hybrid` and `generate.hybrid` search methods.
        """
        return _HybridNearVector(vector=vector, distance=distance, certainty=certainty)


class _QueryReference(_WeaviateInput):
    link_on: str
    include_vector: INCLUDE_VECTOR = Field(default=False)
    return_metadata: Optional[MetadataQuery] = Field(default=None)
    return_properties: Union["PROPERTIES", bool, None] = Field(default=None)
    return_references: Optional["REFERENCES"] = Field(default=None)

    def __hash__(self) -> int:  # for set
        return hash(str(self))

    @property
    def _return_metadata(self) -> _MetadataQuery:
        return _MetadataQuery.from_public(self.return_metadata, self.include_vector)


class _QueryReferenceMultiTarget(_QueryReference):
    target_collection: str


class QueryReference(_QueryReference):
    """Define a query-time reference to a single-target property when querying through cross-references."""

    MultiTarget: ClassVar[Type[_QueryReferenceMultiTarget]] = _QueryReferenceMultiTarget
    """Define a query-time reference to a multi-target property when querying through cross-references."""


class QueryNested(_WeaviateInput):
    """Define the query-time return properties of a nested property."""

    name: str
    properties: "PROPERTIES"

    def __hash__(self) -> int:  # for set
        return hash(str(self))


REFERENCE = Union[_QueryReference, _QueryReferenceMultiTarget]
REFERENCES = Union[Sequence[REFERENCE], REFERENCE]

PROPERTY = Union[str, QueryNested]
PROPERTIES = Union[Sequence[PROPERTY], PROPERTY]

NestedProperties = Union[List[Union[str, QueryNested]], str, QueryNested]


class NearMediaType(str, Enum):
    """The different types of media that can be used in a `near_media` query to leverage the `multi2vec-*` modules.

    All are available when using `multi2vec-bind` but only `IMAGE` is available when using `multi2vec-clip`.
    """

    AUDIO = "audio"
    DEPTH = "depth"
    IMAGE = "image"
    IMU = "imu"
    THERMAL = "thermal"
    VIDEO = "video"
