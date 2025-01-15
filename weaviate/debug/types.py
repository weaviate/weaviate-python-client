from datetime import datetime
from typing import Any, Dict, Optional

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
