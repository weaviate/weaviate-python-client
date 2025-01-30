from typing import List, Optional, Union

import httpx
from pydantic import BaseModel

from weaviate.agents.query.models import (
    AggregationResult,
    CollectionDescription,
    QueryResult,
    Usage,
)
from weaviate.client import WeaviateAsyncClient, WeaviateClient


class WeaviateSearchAgentSimpleResponse(BaseModel):
    original_query: str
    collection_names: list[str]
    searches: list[list[QueryResult]]
    aggregations: list[list[AggregationResult]]
    usage: Usage
    total_time: float
    search_answer: str | None
    aggregation_answer: str | None
    has_aggregation_answer: bool
    has_search_answer: bool
    is_partial_answer: bool
    missing_information: list[str]
    final_answer: str


class QueryAgentError(Exception):
    """Error raised by the QueryAgent."""


class QueryAgent:
    """Agent class for performing agentic queries against Weaviate collections."""

    def __init__(
        self,
        client: Union[WeaviateClient, WeaviateAsyncClient],
        collections: List[Union[str, CollectionDescription]],
        agents_host: Union[str, None] = None,
    ):
        """Initialize a QueryAgent.

        Args:
            client: A Weaviate client instance (sync or async)
            collections: List of collection names or CollectionDescription objects the agent has access to
        """
        self._client = client
        self._connection = client._connection
        self._agents_host = agents_host or "https://gfl.labs.weaviate.io"
        self._collections = collections

        # check if all collections have the same URL
        self.base_url = self._client._connection.url

        self._headers = {"Content-Type": "application/json"}
        self._headers.update(self._connection.additional_headers)
        self._timeout = 40

        self._cluster_host = self.base_url.replace(":443", "")

        # Store token for use in request body instead of headers
        self._token = self._connection.get_current_bearer_token().replace("Bearer ", "")

        self._query_agent_url = f"{self._agents_host}/agent/query"

    def run(
        self,
        query: str,
        view_properties: Optional[List[str]] = None,
    ) -> WeaviateSearchAgentSimpleResponse:
        """Execute a agentic query against the specified collections.

        Args:
            query: The natural language query string
            view_properties: Optional list of property names which the agent has the ability to view

        Returns:
            A WeaviateSearchAgentSimpleResponse object containing search results and analysis
        """
        request_body = {
            "query": query,
            "weaviate_cloud_details": {
                "url": self._cluster_host,
                "key": self._token,
            },
            "collection_names": [
                c.name if isinstance(c, CollectionDescription) else c for c in self._collections
            ],
            "agent_type": "simple",
            "headers": self._headers,
            "collection_view_properties": view_properties,
            "limit": 20,
            "tenant": None,
        }

        response = httpx.post(
            self._query_agent_url,
            headers=self._headers,
            json=request_body,
            timeout=self._timeout,
        )

        if response.status_code != 200:
            raise QueryAgentError(
                f"Query agent returned status code {response.status_code} with response {response.text}"
            )

        return WeaviateSearchAgentSimpleResponse(**response.json())