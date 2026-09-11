"""Export models and enums."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from weaviate.backup.backup import BackupStorage

ExportStorage = BackupStorage


class ExportFileFormat(str, Enum):
    """Which file format should be used for the export."""

    PARQUET = "parquet"


class ExportStatus(str, Enum):
    """The status of an export."""

    STARTED = "STARTED"
    TRANSFERRING = "TRANSFERRING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class ShardExportStatus(str, Enum):
    """The status of an individual shard export."""

    TRANSFERRING = "TRANSFERRING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ShardProgress(BaseModel):
    """Progress of a single shard export."""

    status: ShardExportStatus
    objects_exported: int = Field(alias="objectsExported", default=0)
    error: Optional[str] = None
    skip_reason: Optional[str] = Field(alias="skipReason", default=None)

    model_config = {"populate_by_name": True}


class ExportCreateReturn(BaseModel):
    """Return type of the export creation method."""

    export_id: str = Field(alias="id")
    backend: str
    path: str
    status: ExportStatus
    started_at: Optional[datetime] = Field(alias="startedAt", default=None)
    collections: List[str] = Field(default_factory=list, alias="classes")

    model_config = {"populate_by_name": True}


class ExportStatusReturn(ExportCreateReturn):
    """Return type of the export status method."""

    completed_at: Optional[datetime] = Field(alias="completedAt", default=None)
    shard_status: Optional[Dict[str, Dict[str, ShardProgress]]] = Field(
        alias="shardStatus", default=None
    )
    error: Optional[str] = None
    took_in_ms: Optional[int] = Field(alias="tookInMs", default=None)
