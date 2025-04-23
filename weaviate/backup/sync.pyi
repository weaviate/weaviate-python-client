import asyncio
import time
from typing import Generic, Optional, Union, List, Tuple, Dict
from httpx import Response
from weaviate.backup.backup import (
    BackupStorage,
    BackupReturn,
    BackupStatusReturn,
    STORAGE_NAMES,
    BackupConfigCreate,
    BackupStatus,
    BackupConfigRestore,
)
from weaviate.backup.backup_location import BackupLocationType
from weaviate.connect import executor
from weaviate.connect.v4 import _ExpectedStatusCodes, Connection, ConnectionAsync, ConnectionType
from weaviate.exceptions import (
    WeaviateInvalidInputError,
    WeaviateUnsupportedFeatureError,
    BackupFailedException,
    EmptyResponseException,
    BackupCanceledError,
)
from weaviate.util import _capitalize_first_letter, _decode_json_response_dict
from weaviate.connect.v4 import ConnectionSync
from .executor import _BackupExecutor

class _Backup(_BackupExecutor[ConnectionSync]):
    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupReturn: ...
    def get_create_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn: ...
    def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupReturn: ...
    def get_restore_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn: ...
    def cancel(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> bool: ...
