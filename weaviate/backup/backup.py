from datetime import datetime
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
    ZSTD_BEST_SPEED = "ZstdBestSpeed"
    ZSTD_DEFAULT = "ZstdDefaultCompression"
    ZSTD_BEST_COMPRESSION = "ZstdBestCompression"
    NO_COMPRESSION = "NoCompression"


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
    CANCELLING = "CANCELLING"
    FINALIZING = "FINALIZING"
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

    ChunkSize: Optional[int] = Field(
        default=None,
        alias="chunk_size",
        description="DEPRECATED: This parameter no longer has any effect.",
        exclude=True,
    )
    CompressionLevel: Optional[BackupCompressionLevel] = Field(
        default=None, alias="compression_level"
    )
    dedupeReplicas: Optional[bool] = Field(
        default=None,
        alias="dedupe_replicas",
        description=(
            "If True, shards of replicated collections that are provably in sync (via async-replication "
            "checkpoints) are archived by a single replica instead of every replica, and a restore copies "
            "them back to all replicas. Shards that cannot be proven in sync fall back to being archived "
            "by every replica. Requires async replication on replicated collections, a cluster where every "
            "node supports this option, and ``BACKUP_DEDUPE_ENABLED=true`` on the cluster, otherwise the "
            "request is rejected with 422. A backup where at least one shard was deduplicated can only be "
            "restored by versions that support this option, and its restore can block the restore request "
            "for up to two minutes; size the client's ``insert`` timeout accordingly. "
            "Requires Weaviate 1.40.0."
        ),
    )
    dedupeConvergenceTimeoutSeconds: Optional[int] = Field(
        default=None,
        alias="dedupe_convergence_timeout_seconds",
        description=(
            "How long (1-600 seconds, server default 60) the coordinator waits for replica convergence proof "
            "before shards fall back to being archived by every replica. Only used when ``dedupe_replicas`` is "
            "True. The wait happens synchronously inside the backup creation request, which blocks for roughly "
            "10 seconds plus up to this timeout; size the client's ``insert`` timeout accordingly. "
            "Requires Weaviate 1.40.0."
        ),
    )

    def _uses_dedupe(self) -> bool:
        return self.dedupeReplicas is not None or self.dedupeConvergenceTimeoutSeconds is not None


class BackupConfigRestore(_BackupConfigBase):
    """Options to configure the backup when restoring a backup."""


class BackupStatusReturn(BaseModel):
    """Return type of the backup status methods."""

    error: Optional[str] = Field(default=None)
    status: BackupStatus
    path: str
    backup_id: str = Field(alias="id")
    size: float = Field(default=0)


class BackupReturn(BackupStatusReturn):
    """Return type of the backup creation and restore methods."""

    collections: List[str] = Field(default_factory=list, alias="classes")


class BackupListReturn(BaseModel):
    """Return type of the backup list method."""

    collections: List[str] = Field(default_factory=list, alias="classes")
    status: BackupStatus
    backup_id: str = Field(alias="id")
    started_at: Optional[datetime] = Field(alias="startedAt", default=None)
    completed_at: Optional[datetime] = Field(alias="completedAt", default=None)
    size: float = Field(default=0)
    # None when the backup is not incremental, and also when the server omits the
    # field: it is only returned to callers Weaviate has confirmed as root.
    incremental_base_backup_id: Optional[str] = Field(default=None)
