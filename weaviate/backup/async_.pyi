import asyncio
import time
from typing import Dict, Generic, List, Optional, Tuple, Union
from httpx import Response
from weaviate.backup.backup import (
    STORAGE_NAMES,
    BackupConfigCreate,
    BackupConfigRestore,
    BackupReturn,
    BackupStatus,
    BackupStatusReturn,
    BackupStorage,
)
from weaviate.backup.backup_location import BackupLocationType
from weaviate.connect import executor
from weaviate.connect.v4 import Connection, ConnectionAsync, ConnectionType, _ExpectedStatusCodes
from weaviate.exceptions import (
    BackupCanceledError,
    BackupFailedException,
    EmptyResponseException,
    WeaviateInvalidInputError,
    WeaviateUnsupportedFeatureError,
)
from weaviate.util import _capitalize_first_letter, _decode_json_response_dict
from weaviate.connect.v4 import ConnectionAsync
from .executor import _BackupExecutor

class _BackupAsync(_BackupExecutor[ConnectionAsync]):
    async def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupReturn: ...
    async def get_create_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn: ...
    async def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupReturn: ...
    async def get_restore_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn: ...
    async def cancel(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> bool: ...
