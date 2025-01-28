from typing import List, Optional, Union

import httpx

from weaviate.client import WeaviateClient

from .models import (
    AppendPropertyOperation,
    DependentOperationStep,
    OperationStep,
    OperationType,
    TransformationResponse,
)


class TransformationAgent:
    """Agent for running transformation operations on a collection."""

    def __init__(
        self,
        client: WeaviateClient,
        collection: str,
        operations: List[Union[OperationStep, DependentOperationStep]],
        agents_host: Optional[str] = None,
    ) -> None:
        """Initialize the transformation agent.

        Args:
            client: The Weaviate client
            collection: The name of the collection to transform
            operations: List of operations to perform, with optional dependencies
        """
        self._client = client
        self._connection = client._connection
        self._collection = collection
        self._operations = operations

        # Set up connection details
        self._agents_host = agents_host or "https://gfl.labs.weaviate.io"
        self._cluster_host = self._connection.url.replace(":443", "")
        self._headers = {"Content-Type": "application/json"}
        self._headers.update(self._connection.additional_headers)
        self._timeout = 40

        # Store token for use in request body
        self._token = self._connection.get_current_bearer_token().replace("Bearer ", "")

    async def _execute_append_operation(
        self, operation: AppendPropertyOperation
    ) -> TransformationResponse:
        """Execute an append transformation operation."""
        request_body = {
            "instruction": operation.instruction,
            "view_properties": operation.view_properties,
            "collection": self._collection,
            "weaviate": {
                "url": self._cluster_host,
                "key": self._token,
            },
            "headers": self._headers,
            "on_properties": [
                {
                    "name": operation.property_name,
                    "data_type": operation.data_type.value,
                }
            ],
        }

        async with httpx.AsyncClient(base_url=self._agents_host) as client:
            response = await client.post(
                "/gfls/create",
                headers=self._headers,
                json=request_body,
                timeout=self._timeout,
            )

            if response.status_code >= 400:
                raise Exception(f"Operation failed: {response.text}")

            # Create TransformationResponse with both operation name and workflow ID
            response_data = response.json()
            return TransformationResponse(
                operation_name=operation.property_name, workflow_id=response_data["workflow_id"]
            )

    async def _execute_update_operation(self, operation: OperationStep) -> TransformationResponse:
        """Execute an update transformation operation."""
        request_body = {
            "instruction": operation.instruction,
            "view_properties": operation.view_properties,
            "collection": self._collection,
            "weaviate": {
                "url": self._cluster_host,
                "key": self._token,
            },
            "headers": self._headers,
            "on_properties": [operation.property_name],
        }

        async with httpx.AsyncClient(base_url=self._agents_host) as client:
            response = await client.post(
                "/gfls/update",
                headers=self._headers,
                json=request_body,
                timeout=self._timeout,
            )

            if response.status_code >= 400:
                raise Exception(f"Operation failed: {response.text}")

            # Create TransformationResponse with both operation name and workflow ID
            response_data = response.json()
            return TransformationResponse(
                operation_name=operation.property_name, workflow_id=response_data["workflow_id"]
            )

    async def _execute_operation(self, operation: OperationStep) -> TransformationResponse:
        """Execute a single transformation operation."""
        if operation.operation_type == OperationType.APPEND:
            if not isinstance(operation, AppendPropertyOperation):
                raise ValueError("Append operations must use AppendPropertyOperation type")
            return await self._execute_append_operation(operation)
        return await self._execute_update_operation(operation)

    @classmethod
    def configure(
        cls,
        client: WeaviateClient,
        collection: str,
        operations: List[Union[OperationStep, DependentOperationStep]],
    ) -> "TransformationAgent":
        """Configure a new transformation agent.

        Args:
            client: The Weaviate client
            collection: The name of the collection to transform
            operations: List of operations to perform, with optional dependencies

        Returns:
            A configured TransformationAgent
        """
        return cls(client=client, collection=collection, operations=operations)

    async def update_all(self) -> List[TransformationResponse]:
        """Run all transformation operations on the collection.

        Returns:
            List of TransformationResponse objects containing operation names and workflow IDs
        """
        responses = []
        for operation in self._operations:
            if isinstance(operation, DependentOperationStep):
                op = operation.operation
            else:
                op = operation

            # Just use the response directly since it now includes operation_name
            responses.append(await self._execute_operation(op))

        return responses
