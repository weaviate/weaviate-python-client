from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from weaviate.collections.classes.config import DataType


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
