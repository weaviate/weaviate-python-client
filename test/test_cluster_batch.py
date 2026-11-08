from unittest.mock import AsyncMock, MagicMock

import pytest

from weaviate.collections.batch.base import _ClusterBatch, _ClusterBatchAsync


def _json_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.status_code = 200
    return response


@pytest.mark.parametrize("payload", [{"nodes": []}, {}])
def test_sync_get_nodes_status_returns_empty_list(payload: dict) -> None:
    connection = MagicMock()
    connection.get.return_value = _json_response(payload)

    cluster = _ClusterBatch(connection)

    assert cluster.get_nodes_status() == []
    assert cluster.get_number_of_nodes() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [{"nodes": []}, {}])
async def test_async_get_nodes_status_matches_sync_for_empty_nodes(payload: dict) -> None:
    connection = MagicMock()
    connection.get = AsyncMock(return_value=_json_response(payload))

    cluster = _ClusterBatchAsync(connection)

    assert await cluster.get_nodes_status() == []
    assert await cluster.get_number_of_nodes() == 0


@pytest.mark.asyncio
async def test_async_get_nodes_status_returns_nodes() -> None:
    nodes = [{"name": "node-1", "status": "HEALTHY"}]
    connection = MagicMock()
    connection.get = AsyncMock(return_value=_json_response({"nodes": nodes}))

    cluster = _ClusterBatchAsync(connection)

    assert await cluster.get_nodes_status() == nodes
