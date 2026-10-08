from typing import List, Literal, Union, overload

from weaviate.connect.v4 import (
    ConnectionSync,
)
from weaviate.export.export import (
    ExportCreateReturn,
    ExportFileFormat,
    ExportStatusReturn,
    ExportStorage,
)

from .executor import _ExportExecutor

class _Export(_ExportExecutor[ConnectionSync]):
    @overload
    def create(
        self,
        *,
        export_id: str,
        backend: ExportStorage,
        file_format: ExportFileFormat,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: Literal[True],
    ) -> ExportStatusReturn: ...
    @overload
    def create(
        self,
        *,
        export_id: str,
        backend: ExportStorage,
        file_format: ExportFileFormat,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: Literal[False] = False,
    ) -> ExportCreateReturn: ...
    def get_status(self, *, export_id: str, backend: ExportStorage) -> ExportStatusReturn: ...
    def cancel(self, *, export_id: str, backend: ExportStorage) -> bool: ...
