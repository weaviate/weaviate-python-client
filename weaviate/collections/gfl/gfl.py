from typing import Any, Dict, List, Optional

from httpx import AsyncClient, HTTPError, Response
from pydantic import BaseModel

from weaviate.collections.classes.config import DataType
from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateConnectionError


class GFLResponse(BaseModel):
    """Response from a GFL operation."""

    workflow_id: str


class GFLStatus(BaseModel):
    """Status of a GFL workflow."""

    parent_state: str
    child_state: str
    batch_count: int
    total_items: int


class GFLStatusResponse(BaseModel):
    """Response from a GFL status operation."""

    workflow_id: str
    status: GFLStatus


class _GFLBase:
    def __init__(self, connection: ConnectionV4, name: str):
        self._connection = connection
        self._name = name
        self._gfl_host = "https://gfl.labs.weaviate.io"
        self._cluster_host = connection.url.replace(":443", "")
        self._headers = {"Content-Type": "application/json"}
        self._headers.update(connection.additional_headers)

        # Store token for use in request body instead of headers
        self._token = self._connection.get_current_bearer_token().replace("Bearer ", "")

        # Create a new AsyncClient for the GFL host
        self._client = AsyncClient(
            base_url=self._gfl_host,
            headers=self._headers,
        )

    async def close(self) -> None:
        await self._client.aclose()

    # Implement the request methods
    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Response:
        try:
            response = await self._client.get(path, params=params)
            response.raise_for_status()
            return response
        except HTTPError as e:
            raise WeaviateConnectionError(f"GET request failed: {e}") from e

    async def post(self, path: str, json: Optional[Dict[str, Any]] = None) -> Response:
        try:
            response = await self._client.post(path, json=json)
            # response.raise_for_status()
            if response.status_code >= 400:
                error_message = f"Error {response.status_code}: {response.text}"
                print(error_message)
            return response
        except HTTPError as e:
            raise WeaviateConnectionError(f"POST request failed: {e}") from e

    async def put(self, path: str, json: Optional[Dict[str, Any]] = None) -> Response:
        try:
            response = await self._client.put(path, json=json)
            response.raise_for_status()
            return response
        except HTTPError as e:
            raise WeaviateConnectionError(f"PUT request failed: {e}") from e

    async def delete(self, path: str) -> Response:
        try:
            response = await self._client.delete(path)
            response.raise_for_status()
            return response
        except HTTPError as e:
            raise WeaviateConnectionError(f"DELETE request failed: {e}") from e


class _GFLAsync(_GFLBase):
    async def create(
        self,
        property_name: str,
        data_type: DataType,
        view_properties: List[str],
        instruction: str,
        uuids: Optional[List[str]] = None,
        tenant: Optional[str] = None,
        model: str = "weaviate",
        api_key_for_model: Optional[str] = None,
    ) -> GFLResponse:
        """
        Triggers a Generative Feedback Loop (GFL) that creates a new property on the collection of data type `data_type`.

        Args:
            property_name (str): The name of the property to create.
            data_type (DataType): The data type of the property to create.
            view_properties (List[str]): The properties that model can view when generating the new property.
            instruction (str): The instruction to use for the GFL.
            uuids (Optional[List[str]], optional): The UUIDs of the objects to include in the GFL.
            If none are provided, the GFL will be triggered on all objects in the collection. Defaults to None.
            model (str, optional): The model to use for the GFL. Defaults to "weaviate". Other options are "openai"
        """
        response = await self.post(
            "/gfls/create",
            json={
                "uuids": uuids,
                "collection": self._name,
                "instruction": instruction,
                "on_properties": [(property_name, data_type.value)],
                "view_properties": view_properties,
                "weaviate": {
                    "url": self._cluster_host,
                    "key": self._token,
                },
                "headers": self._headers,
                "tenant": tenant,
                "model": model,
                "api_key_for_model": api_key_for_model,
            },
        )
        return GFLResponse.model_validate(response.json())

    async def update(
        self,
        instruction: str,
        view_properties: List[str],
        on_properties: List[str],
        uuids: Optional[List[str]] = None,
        tenant: Optional[str] = None,
        model: str = "weaviate",
        api_key_for_model: Optional[str] = None,
    ) -> GFLResponse:
        """
        Triggers a Generative Feedback Loop (GFL) that updates the property on the collection.

        Args:
            instruction (str): The instruction to use for the GFL.
            view_properties (List[str]): The properties that model can view when generating the new property.
            on_properties (List[str]): The properties that model can update.
            uuids (Optional[List[str]], optional): The UUIDs of the objects to include in the GFL.
            If none are provided, the GFL will be triggered on all objects in the collection. Defaults to None.
        """
        response = await self.post(
            "/gfls/update",
            json={
                "uuids": uuids,
                "collection": self._name,
                "instruction": instruction,
                "on_properties": on_properties,
                "view_properties": view_properties,
                "weaviate": {
                    "url": self._cluster_host,
                    "key": self._token,
                },
                "headers": self._headers,
                "tenant": tenant,
                "model": model,
                "api_key_for_model": api_key_for_model,
            },
        )
        return GFLResponse.model_validate(response.json())

    async def status(self, workflow_id: str) -> GFLStatusResponse:
        """Get the status of a GFL workflow."""
        response = await self.get(f"/gfls/status/{workflow_id}")
        return GFLStatusResponse.model_validate(response.json())


class _GFLCreateOperationAsync:
    def __init__(self, gfl_collection: _GFLAsync):
        self._gfl_collection = gfl_collection

    async def with_hybrid_search(
        self, query: str, alpha: float, limit: int, properties: List[str]
    ) -> "_GFLCreateOperationAsync":
        # Implementation for with_hybrid_search
        return self

    async def with_filters(self, filters: dict) -> "_GFLCreateOperationAsync":
        # Implementation for with_filters
        return self
