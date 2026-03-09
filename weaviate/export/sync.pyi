from typing import List, Optional, Union

from weaviate.connect.v4 import ConnectionSync
from weaviate.export.export import (
    ExportConfig,
    ExportCreateReturn,
    ExportFileFormat,
    ExportStatusReturn,
    ExportStorage,
)

from .executor import _ExportExecutor

class _Export(_ExportExecutor[ConnectionSync]):
    def create(
        self,
        export_id: str,
        backend: ExportStorage,
        file_format: ExportFileFormat,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[ExportConfig] = None,
    ) -> ExportCreateReturn: ...
    def get_status(
        self,
        export_id: str,
        backend: ExportStorage,
        bucket: Optional[str] = None,
        path: Optional[str] = None,
    ) -> ExportStatusReturn: ...
    def cancel(
        self,
        export_id: str,
        backend: ExportStorage,
        bucket: Optional[str] = None,
        path: Optional[str] = None,
    ) -> bool: ...
