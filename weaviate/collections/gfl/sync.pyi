from typing import Dict, List, Optional

from weaviate.collections.classes.config import DataType
from weaviate.collections.gfl.gfl import GFLResponse, GFLStatusResponse, _GFLBase

class _GFL(_GFLBase):
    def create(
        self,
        property_name: str,
        data_type: DataType,
        view_properties: List[str],
        instruction: str,
        uuids: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        tenant: Optional[str] = None,
        model: str = "weaviate",
        api_key_for_model: Optional[str] = None,
    ) -> GFLResponse: ...
    def update(
        self,
        instruction: str,
        view_properties: List[str],
        on_properties: List[str],
        uuids: Optional[List[str]] = None,
        headers: Optional[Dict[str, str]] = None,
        tenant: Optional[str] = None,
        model: str = "weaviate",
        api_key_for_model: Optional[str] = None,
    ) -> GFLResponse: ...
    def delete_object(self, instruction: str, view_properties: List[str]) -> None: ...
    def status(self, workflow_id: str) -> GFLStatusResponse: ...
