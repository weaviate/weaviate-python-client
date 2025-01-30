from enum import Enum
from typing import Dict, Literal, Optional, Union, List

from pydantic import BaseModel

from weaviate.collections.classes.config import DataType

class CollectionDescription(BaseModel):
    name: str
    description: str


class ComparisonOperator(str, Enum):
    EQUALS = "="
    LESS_THAN = "<"
    GREATER_THAN = ">"
    LESS_EQUAL = "<="
    GREATER_EQUAL = ">="
    NOT_EQUALS = "!="
    LIKE = "LIKE"


class IntegerPropertyFilter(BaseModel):
    """Filter numeric properties using comparison operators."""

    property_name: str
    operator: ComparisonOperator
    value: float


class TextPropertyFilter(BaseModel):
    """Filter text properties using equality or LIKE operators"""

    property_name: str
    operator: ComparisonOperator
    value: str


class BooleanPropertyFilter(BaseModel):
    """Filter boolean properties using equality operators"""

    property_name: str
    operator: ComparisonOperator
    value: bool


class QueryResult(BaseModel):

    queries: list[str]
    filters: list[list[Union[BooleanPropertyFilter, IntegerPropertyFilter, TextPropertyFilter]]] = (
        []
    )
    filter_operators: Literal["AND", "OR"]


class NumericMetrics(str, Enum):
    COUNT = "COUNT"
    MAX = "MAXIMUM"
    MEAN = "MEAN"
    MEDIAN = "MEDIAN"
    MIN = "MINIMUM"
    MODE = "MODE"
    SUM = "SUM"
    TYPE = "TYPE"


class TextMetrics(str, Enum):
    COUNT = "COUNT"
    TYPE = "TYPE"
    TOP_OCCURRENCES = "TOP_OCCURRENCES"


class BooleanMetrics(str, Enum):
    COUNT = "COUNT"
    TYPE = "TYPE"
    TOTAL_TRUE = "TOTAL_TRUE"
    TOTAL_FALSE = "TOTAL_FALSE"
    PERCENTAGE_TRUE = "PERCENTAGE_TRUE"
    PERCENTAGE_FALSE = "PERCENTAGE_FALSE"


class IntegerPropertyAggregation(BaseModel):
    """Aggregate numeric properties using statistical functions"""

    property_name: str
    metrics: NumericMetrics


class TextPropertyAggregation(BaseModel):
    """Aggregate text properties using frequency analysis"""

    property_name: str
    metrics: TextMetrics
    top_occurrences_limit: Optional[int] = None


class BooleanPropertyAggregation(BaseModel):
    """Aggregate boolean properties using statistical functions"""

    property_name: str
    metrics: BooleanMetrics


class AggregationResult(BaseModel):
    """
    The aggregations to be performed on a collection in a vector database.

    They should be based on the original user query and can include multiple
    aggregations across different properties and metrics.
    """

    search_query: Optional[str] = None
    groupby_property: Optional[str] = None
    aggregations: list[
        Union[
            IntegerPropertyAggregation,
            TextPropertyAggregation,
            BooleanPropertyAggregation,
        ]
    ]


class Usage(BaseModel):
    requests: Union[int, str] = 0
    request_tokens: Union[int, str, None] = None
    response_tokens: Union[int, str, None] = None
    total_tokens: Union[int, str, None] = None
    details: Union[Dict[str, int], Dict[str, str], None] = None

class OperationType(str, Enum):
    """Types of operations that can be performed on properties."""

    APPEND = "append"
    UPDATE = "update"


class OperationStep(BaseModel):
    """Base model for a transformation operation step."""

    property_name: str
    view_properties: List[str]
    instruction: str
    operation_type: OperationType


class AppendPropertyOperation(OperationStep):
    """Operation to append a new property."""

    data_type: DataType
    operation_type: OperationType = OperationType.APPEND


class UpdatePropertyOperation(OperationStep):
    """Operation to update an existing property."""

    operation_type: OperationType = OperationType.UPDATE


class DependentOperationStep(BaseModel):
    """A wrapper for operation steps that have dependencies on other operations."""

    operation: OperationStep
    depends_on: Optional[List[OperationStep]] = None

    def __init__(
        self, operation: OperationStep, depends_on: Optional[List[OperationStep]] = None
    ) -> None:
        super().__init__(operation=operation, depends_on=depends_on or [])


class TransformationResponse(BaseModel):
    """Response from a GFL operation."""

    operation_name: str
    workflow_id: str