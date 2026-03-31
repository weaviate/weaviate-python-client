from typing import List, Literal, Optional, Union, overload

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
    @overload
    async def create(
        self,
        export_id: str,
        backend: ExportStorage,
        file_format: ExportFileFormat,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        *,
        wait_for_completion: Literal[True],
        config: Optional[ExportConfig] = None,
    ) -> ExportStatusReturn: ...
    @overload
    async def create(
        self,
        export_id: str,
        backend: ExportStorage,
        file_format: ExportFileFormat,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: Literal[False] = False,
        config: Optional[ExportConfig] = None,
    ) -> ExportCreateReturn: ...
    async def get_status(
        self, export_id: str, backend: ExportStorage, config: Optional[ExportConfig] = None
    ) -> ExportStatusReturn: ...
    async def cancel(
        self, export_id: str, backend: ExportStorage, config: Optional[ExportConfig] = None
    ) -> bool: ...
