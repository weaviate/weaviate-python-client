from weaviate.proto.v1 import base_pb2 as _base_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Iterable as _Iterable,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class AggregateRequest(_message.Message):
    __slots__ = (
        "collection",
        "tenant",
        "objects_count",
        "aggregations",
        "object_limit",
        "group_by",
        "limit",
        "filters",
    )

    class Aggregation(_message.Message):
        __slots__ = ("property", "int", "number", "text", "boolean", "date", "reference")

        class Integer(_message.Message):
            __slots__ = ("count", "type", "sum", "mean", "mode", "median", "maximum", "minimum")
            COUNT_FIELD_NUMBER: _ClassVar[int]
            TYPE_FIELD_NUMBER: _ClassVar[int]
            SUM_FIELD_NUMBER: _ClassVar[int]
            MEAN_FIELD_NUMBER: _ClassVar[int]
            MODE_FIELD_NUMBER: _ClassVar[int]
            MEDIAN_FIELD_NUMBER: _ClassVar[int]
            MAXIMUM_FIELD_NUMBER: _ClassVar[int]
            MINIMUM_FIELD_NUMBER: _ClassVar[int]
            count: bool
            type: bool
            sum: bool
            mean: bool
            mode: bool
            median: bool
            maximum: bool
            minimum: bool
            def __init__(
                self,
                count: bool = ...,
                type: bool = ...,
                sum: bool = ...,
                mean: bool = ...,
                mode: bool = ...,
                median: bool = ...,
                maximum: bool = ...,
                minimum: bool = ...,
            ) -> None: ...

        class Number(_message.Message):
            __slots__ = ("count", "type", "sum", "mean", "mode", "median", "maximum", "minimum")
            COUNT_FIELD_NUMBER: _ClassVar[int]
            TYPE_FIELD_NUMBER: _ClassVar[int]
            SUM_FIELD_NUMBER: _ClassVar[int]
            MEAN_FIELD_NUMBER: _ClassVar[int]
            MODE_FIELD_NUMBER: _ClassVar[int]
            MEDIAN_FIELD_NUMBER: _ClassVar[int]
            MAXIMUM_FIELD_NUMBER: _ClassVar[int]
            MINIMUM_FIELD_NUMBER: _ClassVar[int]
            count: bool
            type: bool
            sum: bool
            mean: bool
            mode: bool
            median: bool
            maximum: bool
            minimum: bool
            def __init__(
                self,
                count: bool = ...,
                type: bool = ...,
                sum: bool = ...,
                mean: bool = ...,
                mode: bool = ...,
                median: bool = ...,
                maximum: bool = ...,
                minimum: bool = ...,
            ) -> None: ...

        class Text(_message.Message):
            __slots__ = ("count", "type", "top_occurences", "top_occurences_limit")
            COUNT_FIELD_NUMBER: _ClassVar[int]
            TYPE_FIELD_NUMBER: _ClassVar[int]
            TOP_OCCURENCES_FIELD_NUMBER: _ClassVar[int]
            TOP_OCCURENCES_LIMIT_FIELD_NUMBER: _ClassVar[int]
            count: bool
            type: bool
            top_occurences: bool
            top_occurences_limit: int
            def __init__(
                self,
                count: bool = ...,
                type: bool = ...,
                top_occurences: bool = ...,
                top_occurences_limit: _Optional[int] = ...,
            ) -> None: ...

        class Boolean(_message.Message):
            __slots__ = (
                "count",
                "type",
                "total_true",
                "total_false",
                "percentage_true",
                "percentage_false",
            )
            COUNT_FIELD_NUMBER: _ClassVar[int]
            TYPE_FIELD_NUMBER: _ClassVar[int]
            TOTAL_TRUE_FIELD_NUMBER: _ClassVar[int]
            TOTAL_FALSE_FIELD_NUMBER: _ClassVar[int]
            PERCENTAGE_TRUE_FIELD_NUMBER: _ClassVar[int]
            PERCENTAGE_FALSE_FIELD_NUMBER: _ClassVar[int]
            count: bool
            type: bool
            total_true: bool
            total_false: bool
            percentage_true: bool
            percentage_false: bool
            def __init__(
                self,
                count: bool = ...,
                type: bool = ...,
                total_true: bool = ...,
                total_false: bool = ...,
                percentage_true: bool = ...,
                percentage_false: bool = ...,
            ) -> None: ...

        class Date(_message.Message):
            __slots__ = ("count", "type", "median", "mode", "maximum", "minimum")
            COUNT_FIELD_NUMBER: _ClassVar[int]
            TYPE_FIELD_NUMBER: _ClassVar[int]
            MEDIAN_FIELD_NUMBER: _ClassVar[int]
            MODE_FIELD_NUMBER: _ClassVar[int]
            MAXIMUM_FIELD_NUMBER: _ClassVar[int]
            MINIMUM_FIELD_NUMBER: _ClassVar[int]
            count: bool
            type: bool
            median: bool
            mode: bool
            maximum: bool
            minimum: bool
            def __init__(
                self,
                count: bool = ...,
                type: bool = ...,
                median: bool = ...,
                mode: bool = ...,
                maximum: bool = ...,
                minimum: bool = ...,
            ) -> None: ...

        class Reference(_message.Message):
            __slots__ = ("type", "pointing_to")
            TYPE_FIELD_NUMBER: _ClassVar[int]
            POINTING_TO_FIELD_NUMBER: _ClassVar[int]
            type: bool
            pointing_to: bool
            def __init__(self, type: bool = ..., pointing_to: bool = ...) -> None: ...

        PROPERTY_FIELD_NUMBER: _ClassVar[int]
        INT_FIELD_NUMBER: _ClassVar[int]
        NUMBER_FIELD_NUMBER: _ClassVar[int]
        TEXT_FIELD_NUMBER: _ClassVar[int]
        BOOLEAN_FIELD_NUMBER: _ClassVar[int]
        DATE_FIELD_NUMBER: _ClassVar[int]
        REFERENCE_FIELD_NUMBER: _ClassVar[int]
        property: str
        int: AggregateRequest.Aggregation.Integer
        number: AggregateRequest.Aggregation.Number
        text: AggregateRequest.Aggregation.Text
        boolean: AggregateRequest.Aggregation.Boolean
        date: AggregateRequest.Aggregation.Date
        reference: AggregateRequest.Aggregation.Reference
        def __init__(
            self,
            property: _Optional[str] = ...,
            int: _Optional[_Union[AggregateRequest.Aggregation.Integer, _Mapping]] = ...,
            number: _Optional[_Union[AggregateRequest.Aggregation.Number, _Mapping]] = ...,
            text: _Optional[_Union[AggregateRequest.Aggregation.Text, _Mapping]] = ...,
            boolean: _Optional[_Union[AggregateRequest.Aggregation.Boolean, _Mapping]] = ...,
            date: _Optional[_Union[AggregateRequest.Aggregation.Date, _Mapping]] = ...,
            reference: _Optional[_Union[AggregateRequest.Aggregation.Reference, _Mapping]] = ...,
        ) -> None: ...

    class GroupBy(_message.Message):
        __slots__ = ("collection", "property")
        COLLECTION_FIELD_NUMBER: _ClassVar[int]
        PROPERTY_FIELD_NUMBER: _ClassVar[int]
        collection: str
        property: str
        def __init__(
            self, collection: _Optional[str] = ..., property: _Optional[str] = ...
        ) -> None: ...

    COLLECTION_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    OBJECTS_COUNT_FIELD_NUMBER: _ClassVar[int]
    AGGREGATIONS_FIELD_NUMBER: _ClassVar[int]
    OBJECT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    GROUP_BY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    collection: str
    tenant: str
    objects_count: bool
    aggregations: _containers.RepeatedCompositeFieldContainer[AggregateRequest.Aggregation]
    object_limit: int
    group_by: AggregateRequest.GroupBy
    limit: int
    filters: _base_pb2.Filters
    def __init__(
        self,
        collection: _Optional[str] = ...,
        tenant: _Optional[str] = ...,
        objects_count: bool = ...,
        aggregations: _Optional[_Iterable[_Union[AggregateRequest.Aggregation, _Mapping]]] = ...,
        object_limit: _Optional[int] = ...,
        group_by: _Optional[_Union[AggregateRequest.GroupBy, _Mapping]] = ...,
        limit: _Optional[int] = ...,
        filters: _Optional[_Union[_base_pb2.Filters, _Mapping]] = ...,
    ) -> None: ...

class AggregateReply(_message.Message):
    __slots__ = ("took", "result")

    class Result(_message.Message):
        __slots__ = ("groups",)
        GROUPS_FIELD_NUMBER: _ClassVar[int]
        groups: _containers.RepeatedCompositeFieldContainer[AggregateGroup]
        def __init__(
            self, groups: _Optional[_Iterable[_Union[AggregateGroup, _Mapping]]] = ...
        ) -> None: ...

    TOOK_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    took: float
    result: AggregateReply.Result
    def __init__(
        self,
        took: _Optional[float] = ...,
        result: _Optional[_Union[AggregateReply.Result, _Mapping]] = ...,
    ) -> None: ...

class AggregateGroup(_message.Message):
    __slots__ = ("objects_count", "aggregations", "grouped_by")

    class Aggregations(_message.Message):
        __slots__ = ("aggregations",)

        class Aggregation(_message.Message):
            __slots__ = ("property", "int", "number", "text", "boolean", "date", "reference")

            class Integer(_message.Message):
                __slots__ = ("count", "type", "mean", "median", "mode", "maximum", "minimum", "sum")
                COUNT_FIELD_NUMBER: _ClassVar[int]
                TYPE_FIELD_NUMBER: _ClassVar[int]
                MEAN_FIELD_NUMBER: _ClassVar[int]
                MEDIAN_FIELD_NUMBER: _ClassVar[int]
                MODE_FIELD_NUMBER: _ClassVar[int]
                MAXIMUM_FIELD_NUMBER: _ClassVar[int]
                MINIMUM_FIELD_NUMBER: _ClassVar[int]
                SUM_FIELD_NUMBER: _ClassVar[int]
                count: int
                type: str
                mean: float
                median: float
                mode: int
                maximum: int
                minimum: int
                sum: int
                def __init__(
                    self,
                    count: _Optional[int] = ...,
                    type: _Optional[str] = ...,
                    mean: _Optional[float] = ...,
                    median: _Optional[float] = ...,
                    mode: _Optional[int] = ...,
                    maximum: _Optional[int] = ...,
                    minimum: _Optional[int] = ...,
                    sum: _Optional[int] = ...,
                ) -> None: ...

            class Number(_message.Message):
                __slots__ = ("count", "type", "mean", "median", "mode", "maximum", "minimum", "sum")
                COUNT_FIELD_NUMBER: _ClassVar[int]
                TYPE_FIELD_NUMBER: _ClassVar[int]
                MEAN_FIELD_NUMBER: _ClassVar[int]
                MEDIAN_FIELD_NUMBER: _ClassVar[int]
                MODE_FIELD_NUMBER: _ClassVar[int]
                MAXIMUM_FIELD_NUMBER: _ClassVar[int]
                MINIMUM_FIELD_NUMBER: _ClassVar[int]
                SUM_FIELD_NUMBER: _ClassVar[int]
                count: int
                type: str
                mean: float
                median: float
                mode: float
                maximum: float
                minimum: float
                sum: float
                def __init__(
                    self,
                    count: _Optional[int] = ...,
                    type: _Optional[str] = ...,
                    mean: _Optional[float] = ...,
                    median: _Optional[float] = ...,
                    mode: _Optional[float] = ...,
                    maximum: _Optional[float] = ...,
                    minimum: _Optional[float] = ...,
                    sum: _Optional[float] = ...,
                ) -> None: ...

            class Text(_message.Message):
                __slots__ = ("count", "type", "top_occurences")

                class TopOccurrences(_message.Message):
                    __slots__ = ("items",)

                    class TopOccurrence(_message.Message):
                        __slots__ = ("value", "occurs")
                        VALUE_FIELD_NUMBER: _ClassVar[int]
                        OCCURS_FIELD_NUMBER: _ClassVar[int]
                        value: str
                        occurs: int
                        def __init__(
                            self, value: _Optional[str] = ..., occurs: _Optional[int] = ...
                        ) -> None: ...

                    ITEMS_FIELD_NUMBER: _ClassVar[int]
                    items: _containers.RepeatedCompositeFieldContainer[
                        AggregateGroup.Aggregations.Aggregation.Text.TopOccurrences.TopOccurrence
                    ]
                    def __init__(
                        self,
                        items: _Optional[
                            _Iterable[
                                _Union[
                                    AggregateGroup.Aggregations.Aggregation.Text.TopOccurrences.TopOccurrence,
                                    _Mapping,
                                ]
                            ]
                        ] = ...,
                    ) -> None: ...

                COUNT_FIELD_NUMBER: _ClassVar[int]
                TYPE_FIELD_NUMBER: _ClassVar[int]
                TOP_OCCURENCES_FIELD_NUMBER: _ClassVar[int]
                count: int
                type: str
                top_occurences: AggregateGroup.Aggregations.Aggregation.Text.TopOccurrences
                def __init__(
                    self,
                    count: _Optional[int] = ...,
                    type: _Optional[str] = ...,
                    top_occurences: _Optional[
                        _Union[
                            AggregateGroup.Aggregations.Aggregation.Text.TopOccurrences, _Mapping
                        ]
                    ] = ...,
                ) -> None: ...

            class Boolean(_message.Message):
                __slots__ = (
                    "count",
                    "type",
                    "total_true",
                    "total_false",
                    "percentage_true",
                    "percentage_false",
                )
                COUNT_FIELD_NUMBER: _ClassVar[int]
                TYPE_FIELD_NUMBER: _ClassVar[int]
                TOTAL_TRUE_FIELD_NUMBER: _ClassVar[int]
                TOTAL_FALSE_FIELD_NUMBER: _ClassVar[int]
                PERCENTAGE_TRUE_FIELD_NUMBER: _ClassVar[int]
                PERCENTAGE_FALSE_FIELD_NUMBER: _ClassVar[int]
                count: int
                type: str
                total_true: int
                total_false: int
                percentage_true: float
                percentage_false: float
                def __init__(
                    self,
                    count: _Optional[int] = ...,
                    type: _Optional[str] = ...,
                    total_true: _Optional[int] = ...,
                    total_false: _Optional[int] = ...,
                    percentage_true: _Optional[float] = ...,
                    percentage_false: _Optional[float] = ...,
                ) -> None: ...

            class Date(_message.Message):
                __slots__ = ("count", "type", "median", "mode", "maximum", "minimum")
                COUNT_FIELD_NUMBER: _ClassVar[int]
                TYPE_FIELD_NUMBER: _ClassVar[int]
                MEDIAN_FIELD_NUMBER: _ClassVar[int]
                MODE_FIELD_NUMBER: _ClassVar[int]
                MAXIMUM_FIELD_NUMBER: _ClassVar[int]
                MINIMUM_FIELD_NUMBER: _ClassVar[int]
                count: int
                type: str
                median: str
                mode: str
                maximum: str
                minimum: str
                def __init__(
                    self,
                    count: _Optional[int] = ...,
                    type: _Optional[str] = ...,
                    median: _Optional[str] = ...,
                    mode: _Optional[str] = ...,
                    maximum: _Optional[str] = ...,
                    minimum: _Optional[str] = ...,
                ) -> None: ...

            class Reference(_message.Message):
                __slots__ = ("type", "pointing_to")
                TYPE_FIELD_NUMBER: _ClassVar[int]
                POINTING_TO_FIELD_NUMBER: _ClassVar[int]
                type: str
                pointing_to: _containers.RepeatedScalarFieldContainer[str]
                def __init__(
                    self, type: _Optional[str] = ..., pointing_to: _Optional[_Iterable[str]] = ...
                ) -> None: ...

            PROPERTY_FIELD_NUMBER: _ClassVar[int]
            INT_FIELD_NUMBER: _ClassVar[int]
            NUMBER_FIELD_NUMBER: _ClassVar[int]
            TEXT_FIELD_NUMBER: _ClassVar[int]
            BOOLEAN_FIELD_NUMBER: _ClassVar[int]
            DATE_FIELD_NUMBER: _ClassVar[int]
            REFERENCE_FIELD_NUMBER: _ClassVar[int]
            property: str
            int: AggregateGroup.Aggregations.Aggregation.Integer
            number: AggregateGroup.Aggregations.Aggregation.Number
            text: AggregateGroup.Aggregations.Aggregation.Text
            boolean: AggregateGroup.Aggregations.Aggregation.Boolean
            date: AggregateGroup.Aggregations.Aggregation.Date
            reference: AggregateGroup.Aggregations.Aggregation.Reference
            def __init__(
                self,
                property: _Optional[str] = ...,
                int: _Optional[
                    _Union[AggregateGroup.Aggregations.Aggregation.Integer, _Mapping]
                ] = ...,
                number: _Optional[
                    _Union[AggregateGroup.Aggregations.Aggregation.Number, _Mapping]
                ] = ...,
                text: _Optional[
                    _Union[AggregateGroup.Aggregations.Aggregation.Text, _Mapping]
                ] = ...,
                boolean: _Optional[
                    _Union[AggregateGroup.Aggregations.Aggregation.Boolean, _Mapping]
                ] = ...,
                date: _Optional[
                    _Union[AggregateGroup.Aggregations.Aggregation.Date, _Mapping]
                ] = ...,
                reference: _Optional[
                    _Union[AggregateGroup.Aggregations.Aggregation.Reference, _Mapping]
                ] = ...,
            ) -> None: ...

        AGGREGATIONS_FIELD_NUMBER: _ClassVar[int]
        aggregations: _containers.RepeatedCompositeFieldContainer[
            AggregateGroup.Aggregations.Aggregation
        ]
        def __init__(
            self,
            aggregations: _Optional[
                _Iterable[_Union[AggregateGroup.Aggregations.Aggregation, _Mapping]]
            ] = ...,
        ) -> None: ...

    class GroupedBy(_message.Message):
        __slots__ = (
            "path",
            "text",
            "int",
            "boolean",
            "number",
            "texts",
            "ints",
            "booleans",
            "numbers",
            "geo",
        )
        PATH_FIELD_NUMBER: _ClassVar[int]
        TEXT_FIELD_NUMBER: _ClassVar[int]
        INT_FIELD_NUMBER: _ClassVar[int]
        BOOLEAN_FIELD_NUMBER: _ClassVar[int]
        NUMBER_FIELD_NUMBER: _ClassVar[int]
        TEXTS_FIELD_NUMBER: _ClassVar[int]
        INTS_FIELD_NUMBER: _ClassVar[int]
        BOOLEANS_FIELD_NUMBER: _ClassVar[int]
        NUMBERS_FIELD_NUMBER: _ClassVar[int]
        GEO_FIELD_NUMBER: _ClassVar[int]
        path: _containers.RepeatedScalarFieldContainer[str]
        text: str
        int: int
        boolean: bool
        number: float
        texts: _base_pb2.TextArray
        ints: _base_pb2.IntArray
        booleans: _base_pb2.BooleanArray
        numbers: _base_pb2.NumberArray
        geo: _base_pb2.GeoCoordinatesFilter
        def __init__(
            self,
            path: _Optional[_Iterable[str]] = ...,
            text: _Optional[str] = ...,
            int: _Optional[int] = ...,
            boolean: bool = ...,
            number: _Optional[float] = ...,
            texts: _Optional[_Union[_base_pb2.TextArray, _Mapping]] = ...,
            ints: _Optional[_Union[_base_pb2.IntArray, _Mapping]] = ...,
            booleans: _Optional[_Union[_base_pb2.BooleanArray, _Mapping]] = ...,
            numbers: _Optional[_Union[_base_pb2.NumberArray, _Mapping]] = ...,
            geo: _Optional[_Union[_base_pb2.GeoCoordinatesFilter, _Mapping]] = ...,
        ) -> None: ...

    OBJECTS_COUNT_FIELD_NUMBER: _ClassVar[int]
    AGGREGATIONS_FIELD_NUMBER: _ClassVar[int]
    GROUPED_BY_FIELD_NUMBER: _ClassVar[int]
    objects_count: int
    aggregations: AggregateGroup.Aggregations
    grouped_by: AggregateGroup.GroupedBy
    def __init__(
        self,
        objects_count: _Optional[int] = ...,
        aggregations: _Optional[_Union[AggregateGroup.Aggregations, _Mapping]] = ...,
        grouped_by: _Optional[_Union[AggregateGroup.GroupedBy, _Mapping]] = ...,
    ) -> None: ...
