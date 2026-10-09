from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from weaviate.types import uuid_package


class DebugRESTObject(BaseModel):
    collection: str = Field(..., alias="class")
    creation_time: datetime = Field(..., alias="creationTimeUnix")
    last_update_time: datetime = Field(..., alias="lastUpdateTimeUnix")
    properties: Dict[str, Any] = Field(...)
    tenant: Optional[str] = Field(None)
    uuid: uuid_package.UUID = Field(..., alias="id")
    vector: Optional[list[float]] = Field(None)
    vectors: Optional[Dict[str, list[float]]] = Field(None)


class DistributedTaskUnit(BaseModel):
    """A unit of a distributed task."""

    id: str = Field(...)  # noqa: A003
    node_id: str = Field(..., alias="nodeId")
    status: str = Field(...)
    progress: Optional[float] = Field(None)
    error: Optional[str] = Field(None)
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")
    finished_at: Optional[datetime] = Field(None, alias="finishedAt")


class DistributedTask(BaseModel):
    """Metadata about a distributed task running in the cluster."""

    id: str = Field(...)  # noqa: A003
    version: int = Field(...)
    status: str = Field(...)
    started_at: datetime = Field(..., alias="startedAt")
    finished_at: Optional[datetime] = Field(None, alias="finishedAt")
    finished_nodes: List[str] = Field(default_factory=list, alias="finishedNodes")
    error: Optional[str] = Field(None)
    payload: Optional[Dict[str, Any]] = Field(None)
    units: Optional[List[DistributedTaskUnit]] = Field(None)
