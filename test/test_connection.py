"""Unit tests for weaviate.connect.v4 connection-level behaviour that needs no server."""

import asyncio
import inspect
import threading
import time

import grpc
import pytest
from grpc.aio import AioRpcError, Metadata

from weaviate.config import ConnectionConfig
from weaviate.config import Timeout as TimeoutConfig
from weaviate.connect.base import ConnectionParams
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync, _ConnectionBase
from weaviate.exceptions import WeaviateBatchError
from weaviate.proto.v1 import batch_pb2


def test_connection_sync_init_mirrors_the_base_signature() -> None:
    # explicit, typed parameters (no *args/**kwargs pass-through)
    assert (
        inspect.signature(ConnectionSync.__init__).parameters
        == inspect.signature(_ConnectionBase.__init__).parameters
    )


def _connection_async() -> ConnectionAsync:
    return ConnectionAsync(
        connection_params=ConnectionParams.from_url("http://localhost:8080", 50051),
        auth_client_secret=None,
        timeout_config=TimeoutConfig(),
        proxies=None,
        trust_env=False,
        additional_headers=None,
        connection_config=ConnectionConfig(),
    )


def test_async_batch_objects_error_carries_the_grpc_details_only() -> None:
    # like WeaviateQueryError: the message is the server's details, not the whole
    # '<AioRpcError of RPC that terminated with: ...>' repr
    class FailingStub:
        async def BatchObjects(self, request, metadata=None, timeout=None):
            raise AioRpcError(
                grpc.StatusCode.INVALID_ARGUMENT, Metadata(), Metadata(), details="bad object"
            )

    conn = _connection_async()
    conn._connected = True
    conn._grpc_stub = FailingStub()  # type: ignore[assignment]

    with pytest.raises(WeaviateBatchError) as excinfo:
        asyncio.run(
            conn.grpc_batch_objects(batch_pb2.BatchObjectsRequest(), timeout=1, max_retries=0)
        )
    assert excinfo.value.message == "bad object"
    assert "AioRpcError" not in str(excinfo.value)


def test_cancel_refresher_owned_by_another_loop_is_scheduled_not_awaited() -> None:
    # close() from a thread/loop other than the refresher's must not try to await the
    # task (which would hang); it schedules the cancel on the owning loop instead
    loop = asyncio.new_event_loop()
    started = threading.Event()
    holder: dict = {}

    async def forever() -> None:
        started.set()
        await asyncio.sleep(3600)

    def run() -> None:
        holder["task"] = loop.create_task(forever())
        loop.run_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    assert started.wait(timeout=2)
    conn = _connection_async()
    conn._ConnectionBase__token_refresh_task = holder["task"]  # type: ignore[attr-defined]
    try:
        assert conn._cancel_background_token_refresh() is None  # nothing to await here
        deadline = time.monotonic() + 2
        while not holder["task"].done() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert holder["task"].cancelled()
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=2)
        loop.close()
