from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from weaviate.types import uuid_package


class DebugRESTObject(BaseModel):
    collection: str = Field(..., alias="class")
    creation_time: datetime = Field(..., alias="creationTimeUnix")
    last_update_time: datetime = Field(..., alias="lastUpdateTimeUnix")
    properties: dict[str, Any] = Field(...)
    tenant: Optional[str] = Field(None)
    uuid: uuid_package.UUID = Field(..., alias="id")
    vector: Optional[list[float]] = Field(None)
    vectors: Optional[dict[str, list[float]]] = Field(None)
