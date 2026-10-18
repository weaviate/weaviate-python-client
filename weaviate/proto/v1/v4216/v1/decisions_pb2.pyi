from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Annotate(_message.Message):
    __slots__ = ["questions", "provider"]
    QUESTIONS_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    questions: _containers.RepeatedCompositeFieldContainer[DecisionQuestion]
    provider: DecisionsProvider
    def __init__(self, questions: _Optional[_Iterable[_Union[DecisionQuestion, _Mapping]]] = ..., provider: _Optional[_Union[DecisionsProvider, _Mapping]] = ...) -> None: ...

class DecisionsProvider(_message.Message):
    __slots__ = ["typesafeai", "openai", "dummy", "custom"]
    TYPESAFEAI_FIELD_NUMBER: _ClassVar[int]
    OPENAI_FIELD_NUMBER: _ClassVar[int]
    DUMMY_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_FIELD_NUMBER: _ClassVar[int]
    typesafeai: DecisionsTypeSafeAI
    openai: DecisionsOpenAI
    dummy: DecisionsDummy
    custom: DecisionsCustom
    def __init__(self, typesafeai: _Optional[_Union[DecisionsTypeSafeAI, _Mapping]] = ..., openai: _Optional[_Union[DecisionsOpenAI, _Mapping]] = ..., dummy: _Optional[_Union[DecisionsDummy, _Mapping]] = ..., custom: _Optional[_Union[DecisionsCustom, _Mapping]] = ...) -> None: ...

class DecisionsTypeSafeAI(_message.Message):
    __slots__ = ["model", "base_url", "max_documents", "images"]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    MAX_DOCUMENTS_FIELD_NUMBER: _ClassVar[int]
    IMAGES_FIELD_NUMBER: _ClassVar[int]
    model: str
    base_url: str
    max_documents: int
    images: bool
    def __init__(self, model: _Optional[str] = ..., base_url: _Optional[str] = ..., max_documents: _Optional[int] = ..., images: bool = ...) -> None: ...

class DecisionsOpenAI(_message.Message):
    __slots__ = ["model", "base_url", "max_documents"]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    MAX_DOCUMENTS_FIELD_NUMBER: _ClassVar[int]
    model: str
    base_url: str
    max_documents: int
    def __init__(self, model: _Optional[str] = ..., base_url: _Optional[str] = ..., max_documents: _Optional[int] = ...) -> None: ...

class DecisionsDummy(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class DecisionsCustom(_message.Message):
    __slots__ = ["module", "settings"]
    MODULE_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_FIELD_NUMBER: _ClassVar[int]
    module: str
    settings: _struct_pb2.Struct
    def __init__(self, module: _Optional[str] = ..., settings: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class DecisionQuestion(_message.Message):
    __slots__ = ["name", "property", "instructions", "predicate", "choice", "score"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    INSTRUCTIONS_FIELD_NUMBER: _ClassVar[int]
    PREDICATE_FIELD_NUMBER: _ClassVar[int]
    CHOICE_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    name: str
    property: str
    instructions: str
    predicate: DecisionPredicate
    choice: DecisionChoice
    score: DecisionScore
    def __init__(self, name: _Optional[str] = ..., property: _Optional[str] = ..., instructions: _Optional[str] = ..., predicate: _Optional[_Union[DecisionPredicate, _Mapping]] = ..., choice: _Optional[_Union[DecisionChoice, _Mapping]] = ..., score: _Optional[_Union[DecisionScore, _Mapping]] = ...) -> None: ...

class DecisionPredicate(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...

class DecisionChoice(_message.Message):
    __slots__ = ["options"]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    options: _containers.RepeatedCompositeFieldContainer[DecisionOption]
    def __init__(self, options: _Optional[_Iterable[_Union[DecisionOption, _Mapping]]] = ...) -> None: ...

class DecisionOption(_message.Message):
    __slots__ = ["value", "description"]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    value: str
    description: str
    def __init__(self, value: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class DecisionScore(_message.Message):
    __slots__ = ["levels"]
    LEVELS_FIELD_NUMBER: _ClassVar[int]
    levels: _containers.RepeatedCompositeFieldContainer[DecisionLevel]
    def __init__(self, levels: _Optional[_Iterable[_Union[DecisionLevel, _Mapping]]] = ...) -> None: ...

class DecisionLevel(_message.Message):
    __slots__ = ["label", "description"]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    label: str
    description: str
    def __init__(self, label: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class DecisionResult(_message.Message):
    __slots__ = ["answers"]
    ANSWERS_FIELD_NUMBER: _ClassVar[int]
    answers: _containers.RepeatedCompositeFieldContainer[DecisionAnswer]
    def __init__(self, answers: _Optional[_Iterable[_Union[DecisionAnswer, _Mapping]]] = ...) -> None: ...

class DecisionAnswer(_message.Message):
    __slots__ = ["name", "predicate", "choice", "score", "refusal"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PREDICATE_FIELD_NUMBER: _ClassVar[int]
    CHOICE_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    REFUSAL_FIELD_NUMBER: _ClassVar[int]
    name: str
    predicate: DecisionPredicateAnswer
    choice: DecisionChoiceAnswer
    score: DecisionScoreAnswer
    refusal: DecisionRefusal
    def __init__(self, name: _Optional[str] = ..., predicate: _Optional[_Union[DecisionPredicateAnswer, _Mapping]] = ..., choice: _Optional[_Union[DecisionChoiceAnswer, _Mapping]] = ..., score: _Optional[_Union[DecisionScoreAnswer, _Mapping]] = ..., refusal: _Optional[_Union[DecisionRefusal, _Mapping]] = ...) -> None: ...

class DecisionPredicateAnswer(_message.Message):
    __slots__ = ["probability"]
    PROBABILITY_FIELD_NUMBER: _ClassVar[int]
    probability: float
    def __init__(self, probability: _Optional[float] = ...) -> None: ...

class DecisionChoiceAnswer(_message.Message):
    __slots__ = ["choice", "probabilities", "confidence"]
    CHOICE_FIELD_NUMBER: _ClassVar[int]
    PROBABILITIES_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    choice: str
    probabilities: _containers.RepeatedCompositeFieldContainer[DecisionProbability]
    confidence: float
    def __init__(self, choice: _Optional[str] = ..., probabilities: _Optional[_Iterable[_Union[DecisionProbability, _Mapping]]] = ..., confidence: _Optional[float] = ...) -> None: ...

class DecisionScoreAnswer(_message.Message):
    __slots__ = ["score", "probabilities", "confidence"]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    PROBABILITIES_FIELD_NUMBER: _ClassVar[int]
    CONFIDENCE_FIELD_NUMBER: _ClassVar[int]
    score: float
    probabilities: _containers.RepeatedCompositeFieldContainer[DecisionProbability]
    confidence: float
    def __init__(self, score: _Optional[float] = ..., probabilities: _Optional[_Iterable[_Union[DecisionProbability, _Mapping]]] = ..., confidence: _Optional[float] = ...) -> None: ...

class DecisionProbability(_message.Message):
    __slots__ = ["value", "probability"]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    PROBABILITY_FIELD_NUMBER: _ClassVar[int]
    value: str
    probability: float
    def __init__(self, value: _Optional[str] = ..., probability: _Optional[float] = ...) -> None: ...

class DecisionRefusal(_message.Message):
    __slots__ = []
    def __init__(self) -> None: ...
