from typing import List, Optional, Union

from weaviate.connect.v4 import ConnectionAsync
from weaviate.export.export import (
    ExportConfig,
    ExportCreateReturn,
    ExportFileFormat,
    ExportStatusReturn,
    ExportStorage,
)

from .executor import _ExportExecutor

class _ExportAsync(_ExportExecutor[ConnectionAsync]):
    async def create(
        self,
        export_id: str,
        backend: ExportStorage,
        file_format: ExportFileFormat = ExportFileFormat.PARQUET,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[ExportConfig] = None,
    ) -> ExportCreateReturn: ...
    async def get_status(
        self,
        export_id: str,
        backend: ExportStorage,
        bucket: Optional[str] = None,
        path: Optional[str] = None,
    ) -> ExportStatusReturn: ...
    async def cancel(
        self,
        export_id: str,
        backend: ExportStorage,
        bucket: Optional[str] = None,
        path: Optional[str] = None,
    ) -> bool: ...
