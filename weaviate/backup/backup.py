from enum import Enum
from typing import Any, Dict, List, Optional, cast
from pydantic import BaseModel, Field
from weaviate.backup.backup_location import _BackupLocationConfig

STORAGE_NAMES = {
    "filesystem",
    "s3",
    "gcs",
    "azure",
}


class BackupCompressionLevel(str, Enum):
    """Which compression level should be used to compress the backup."""

    DEFAULT = "DefaultCompression"
    BEST_SPEED = "BestSpeed"
    BEST_COMPRESSION = "BestCompression"


class BackupStorage(str, Enum):
    """Which backend should be used to write the backup to."""

    FILESYSTEM = "filesystem"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"


class BackupStatus(str, Enum):
    """The status of a backup."""

    STARTED = "STARTED"
    TRANSFERRING = "TRANSFERRING"
    TRANSFERRED = "TRANSFERRED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class _BackupConfigBase(BaseModel):
    CPUPercentage: Optional[int] = Field(default=None, alias="cpu_percentage")

    def _to_dict(self) -> Dict[str, Any]:
        ret = cast(dict, self.model_dump(exclude_none=True))

        for key, val in ret.items():
            if isinstance(val, _BackupLocationConfig):
                ret[key] = val._to_dict()

        return ret


class BackupConfigCreate(_BackupConfigBase):
    """Options to configure the backup when creating a backup."""

    ChunkSize: Optional[int] = Field(default=None, alias="chunk_size")
    CompressionLevel: Optional[BackupCompressionLevel] = Field(
        default=None, alias="compression_level"
    )


class BackupConfigRestore(_BackupConfigBase):
    """Options to configure the backup when restoring a backup."""


class BackupStatusReturn(BaseModel):
    """Return type of the backup status methods."""

    error: Optional[str] = Field(default=None)
    status: BackupStatus
    path: str
    backup_id: str = Field(alias="id")


class BackupReturn(BackupStatusReturn):
    """Return type of the backup creation and restore methods."""

    collections: List[str] = Field(default_factory=list, alias="classes")
